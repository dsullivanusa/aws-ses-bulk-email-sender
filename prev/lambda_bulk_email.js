const AWS = require('aws-sdk');

// Configure AWS SES
const ses = new AWS.SES({
    region: process.env.AWS_SES_REGION || 'us-east-1'
});

// Configuration from environment variables
const CONFIG = {
    MAX_RECIPIENTS_PER_BATCH: parseInt(process.env.MAX_RECIPIENTS_PER_BATCH) || 50,
    RATE_LIMIT_DELAY: parseInt(process.env.RATE_LIMIT_DELAY) || 100, // milliseconds
    MAX_EMAIL_SIZE: parseInt(process.env.MAX_EMAIL_SIZE) || 10485760, // 10MB
    ALLOWED_DOMAINS: process.env.ALLOWED_SENDER_DOMAINS ? 
        process.env.ALLOWED_SENDER_DOMAINS.split(',') : null,
    ENABLE_LOGGING: process.env.ENABLE_LOGGING === 'true'
};

/**
 * Main Lambda handler for bulk email sending
 */
exports.handler = async (event, context) => {
    console.log('Bulk email request received:', JSON.stringify(event, null, 2));
    
    try {
        // Parse the request
        const requestBody = typeof event.body === 'string' ? 
            JSON.parse(event.body) : event.body;
            
        // Validate the request
        const validationResult = validateEmailRequest(requestBody);
        if (!validationResult.isValid) {
            return createErrorResponse(400, validationResult.errors);
        }
        
        // Extract email data
        const {
            senderName,
            senderEmail,
            replyToEmail,
            subject,
            body,
            recipients,
            timestamp
        } = requestBody;
        
        console.log(`Processing bulk email for ${recipients.length} recipients`);
        
        // Process emails in batches
        const results = await processBulkEmails({
            senderName,
            senderEmail,
            replyToEmail,
            subject,
            body,
            recipients
        });
        
        // Log results
        if (CONFIG.ENABLE_LOGGING) {
            console.log('Email sending results:', JSON.stringify(results, null, 2));
        }
        
        // Return success response
        return createSuccessResponse({
            message: 'Bulk email processing completed',
            totalRecipients: recipients.length,
            successful: results.successful.length,
            failed: results.failed.length,
            results: results
        });
        
    } catch (error) {
        console.error('Lambda execution error:', error);
        
        return createErrorResponse(500, [{
            field: 'general',
            message: 'Internal server error occurred while processing emails'
        }]);
    }
};

/**
 * Validates the incoming email request
 */
function validateEmailRequest(requestBody) {
    const errors = [];
    
    if (!requestBody) {
        errors.push({ field: 'body', message: 'Request body is required' });
        return { isValid: false, errors };
    }
    
    // Required fields validation
    const requiredFields = [
        'senderName',
        'senderEmail', 
        'subject',
        'body',
        'recipients'
    ];
    
    requiredFields.forEach(field => {
        if (!requestBody[field]) {
            errors.push({ 
                field, 
                message: `${field} is required` 
            });
        }
    });
    
    // Email validation
    if (requestBody.senderEmail && !isValidEmail(requestBody.senderEmail)) {
        errors.push({ 
            field: 'senderEmail', 
            message: 'Invalid sender email format' 
        });
    }
    
    if (requestBody.replyToEmail && !isValidEmail(requestBody.replyToEmail)) {
        errors.push({ 
            field: 'replyToEmail', 
            message: 'Invalid reply-to email format' 
        });
    }
    
    // Recipients validation
    if (requestBody.recipients) {
        if (!Array.isArray(requestBody.recipients)) {
            errors.push({ 
                field: 'recipients', 
                message: 'Recipients must be an array' 
            });
        } else if (requestBody.recipients.length === 0) {
            errors.push({ 
                field: 'recipients', 
                message: 'At least one recipient is required' 
            });
        } else {
            // Validate each recipient email
            const invalidEmails = requestBody.recipients.filter(email => !isValidEmail(email));
            if (invalidEmails.length > 0) {
                errors.push({ 
                    field: 'recipients', 
                    message: `Invalid recipient emails: ${invalidEmails.join(', ')}` 
                });
            }
        }
    }
    
    // Domain validation (if configured)
    if (CONFIG.ALLOWED_DOMAINS && requestBody.senderEmail) {
        const senderDomain = requestBody.senderEmail.split('@')[1];
        if (!CONFIG.ALLOWED_DOMAINS.includes(senderDomain)) {
            errors.push({ 
                field: 'senderEmail', 
                message: `Sender domain not allowed: ${senderDomain}` 
            });
        }
    }
    
    // Content size validation
    const bodySize = Buffer.byteLength(requestBody.body || '', 'utf8');
    if (bodySize > CONFIG.MAX_EMAIL_SIZE) {
        errors.push({ 
            field: 'body', 
            message: `Email body too large: ${bodySize} bytes (max: ${CONFIG.MAX_EMAIL_SIZE})` 
        });
    }
    
    return {
        isValid: errors.length === 0,
        errors
    };
}

/**
 * Process bulk emails in batches with rate limiting
 */
async function processBulkEmails(emailData) {
    const { recipients, ...emailContent } = emailData;
    const results = {
        successful: [],
        failed: [],
        totalProcessed: 0
    };
    
    console.log(`Processing ${recipients.length} recipients in batches of ${CONFIG.MAX_RECIPIENTS_PER_BATCH}`);
    
    // Process recipients in batches
    for (let i = 0; i < recipients.length; i += CONFIG.MAX_RECIPIENTS_PER_BATCH) {
        const batch = recipients.slice(i, i + CONFIG.MAX_RECIPIENTS_PER_BATCH);
        console.log(`Processing batch ${Math.floor(i / CONFIG.MAX_RECIPIENTS_PER_BATCH) + 1}: ${batch.length} recipients`);
        
        const batchResults = await processBatch(emailContent, batch);
        
        results.successful.push(...batchResults.successful);
        results.failed.push(...batchResults.failed);
        results.totalProcessed += batch.length;
        
        // Rate limiting between batches
        if (i + CONFIG.MAX_RECIPIENTS_PER_BATCH < recipients.length) {
            await delay(CONFIG.RATE_LIMIT_DELAY);
        }
    }
    
    console.log(`Batch processing completed. Success: ${results.successful.length}, Failed: ${results.failed.length}`);
    
    return results;
}

/**
 * Process a single batch of recipients
 */
async function processBatch(emailContent, recipients) {
    const batchResults = {
        successful: [],
        failed: []
    };
    
    // Send emails concurrently within the batch
    const promises = recipients.map(async (recipient) => {
        try {
            await sendSingleEmail(emailContent, recipient);
            batchResults.successful.push({
                email: recipient,
                status: 'sent',
                timestamp: new Date().toISOString()
            });
        } catch (error) {
            console.error(`Failed to send email to ${recipient}:`, error.message);
            batchResults.failed.push({
                email: recipient,
                status: 'failed',
                error: error.message,
                timestamp: new Date().toISOString()
            });
        }
    });
    
    await Promise.all(promises);
    
    return batchResults;
}

/**
 * Send a single email using AWS SES
 */
async function sendSingleEmail(emailContent, recipient) {
    const {
        senderName,
        senderEmail,
        replyToEmail,
        subject,
        body
    } = emailContent;
    
    const params = {
        Source: `${senderName} <${senderEmail}>`,
        Destination: {
            ToAddresses: [recipient]
        },
        ReplyToAddresses: [replyToEmail || senderEmail],
        Message: {
            Subject: {
                Data: subject,
                Charset: 'UTF-8'
            },
            Body: {
                Text: {
                    Data: body,
                    Charset: 'UTF-8'
                },
                Html: {
                    Data: isHtmlContent(body) ? body : convertToHtml(body),
                    Charset: 'UTF-8'
                }
            }
        },
        ConfigurationSetName: process.env.SES_CONFIGURATION_SET || undefined,
        Tags: [
            {
                Name: 'EmailType',
                Value: 'BulkEmail'
            },
            {
                Name: 'Sender',
                Value: senderEmail
            }
        ]
    };
    
    const result = await ses.sendEmail(params).promise();
    console.log(`Email sent to ${recipient}. MessageId: ${result.MessageId}`);
    
    return result;
}

/**
 * Check if content appears to be HTML
 */
function isHtmlContent(content) {
    return /<[a-z][\s\S]*>/i.test(content);
}

/**
 * Convert plain text to basic HTML
 */
function convertToHtml(text) {
    return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/\n/g, '<br>')
        .replace(/\t/g, '&nbsp;&nbsp;&nbsp;&nbsp;');
}

/**
 * Validate email format
 */
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

/**
 * Create delay for rate limiting
 */
function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Create successful response
 */
function createSuccessResponse(data) {
    return {
        statusCode: 200,
        headers: {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,x-api-key',
            'Access-Control-Allow-Methods': 'POST,OPTIONS'
        },
        body: JSON.stringify({
            success: true,
            ...data
        })
    };
}

/**
 * Create error response
 */
function createErrorResponse(statusCode, errors) {
    return {
        statusCode,
        headers: {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,x-api-key',
            'Access-Control-Allow-Methods': 'POST,OPTIONS'
        },
        body: JSON.stringify({
            success: false,
            errors: Array.isArray(errors) ? errors : [{ 
                field: 'general', 
                message: errors 
            }]
        })
    };
}