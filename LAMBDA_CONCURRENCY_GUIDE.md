# 🚀 Lambda Concurrency Guide for 20,000 Emails

Optimize Lambda concurrency settings for efficient bulk email processing.

---

## 📊 **Current System Analysis**

| **Metric** | **Value** |
|------------|-----------|
| **Total Emails** | 20,000 |
| **Batch Size** | 10 emails per Lambda execution |
| **Total Executions Needed** | 2,000 |
| **Processing Time per Batch** | 20-60 seconds |
| **Current Reserved Concurrency** | Unreserved (using account limit) |
| **Account Concurrency Limit** | 1,000 (default) |

---

## 🎯 **Recommended Reserved Concurrency**

### **For 20,000 Emails:**

| **Scenario** | **Reserved Concurrency** | **Processing Time** | **Pros** | **Cons** |
|-------------|-------------------------|-------------------|----------|----------|
| **Conservative** | **200** | 15-20 minutes | Very stable, low SES rate risk | Slower processing |
| **Balanced** | **400** | 8-12 minutes | Good balance of speed vs. stability | Moderate SES rate risk |
| **Aggressive** | **600** | 5-8 minutes | Fast processing | Higher SES rate risk |
| **Maximum** | **1000** | 3-5 minutes | Fastest possible | High SES rate risk |

### **🏆 My Recommendation: 400 Reserved Concurrency**

**Why 400?**
- ✅ **Optimal Speed**: 8-12 minutes for 20,000 emails
- ✅ **Stable**: Low risk of Lambda throttling
- ✅ **SES-Friendly**: Reduces risk of hitting SES rate limits
- ✅ **Cost-Effective**: Good balance of performance vs. cost

---

## 🚀 **Quick Setup**

### **Set Recommended Concurrency (400):**
```bash
python set_lambda_concurrency.py 400
```

### **Other Options:**
```bash
# Conservative (slower, more stable)
python set_lambda_concurrency.py 200

# Aggressive (faster, higher risk)
python set_lambda_concurrency.py 600

# Remove reserved concurrency (use account limit)
python set_lambda_concurrency.py remove

# Show all recommendations
python set_lambda_concurrency.py recommendations
```

---

## 📈 **Performance Calculations**

### **Processing Time Formula:**
```
Total Time = (Total Executions ÷ Reserved Concurrency) × Average Batch Time
```

### **Examples:**
- **200 Concurrency**: (2,000 ÷ 200) × 0.5 min = **10 minutes**
- **400 Concurrency**: (2,000 ÷ 400) × 0.5 min = **5 minutes**
- **600 Concurrency**: (2,000 ÷ 600) × 0.5 min = **3.3 minutes**

### **Real-World Times (including overhead):**
- **200 Concurrency**: **15-20 minutes**
- **400 Concurrency**: **8-12 minutes**
- **600 Concurrency**: **5-8 minutes**

---

## ⚠️ **Important Considerations**

### **1. SES Rate Limits**
AWS SES has sending rate limits:
- **Sandbox**: 200 emails/day, 1 email/second
- **Production**: Starts at 200 emails/second, can be increased

**Your Current Status**: Production account with higher limits

### **2. Lambda Account Limits**
- **Default**: 1,000 concurrent executions per region
- **Can be increased**: Request limit increase from AWS Support

### **3. Cost Impact**
Higher concurrency = more Lambda invocations = higher cost
- **200 Concurrency**: Lower cost, slower processing
- **400 Concurrency**: Balanced cost/performance
- **600+ Concurrency**: Higher cost, faster processing

---

## 🔍 **Monitoring & Optimization**

### **Key Metrics to Watch:**

| **Metric** | **Good Value** | **Action if High** |
|------------|----------------|-------------------|
| **Lambda Duration** | < 60 seconds | Increase memory |
| **Lambda Errors** | < 1% | Check logs, reduce concurrency |
| **SES Throttling** | 0% | Reduce concurrency or request limit increase |
| **SQS Queue Depth** | Decreasing | Good - processing faster than queuing |

### **CloudWatch Alarms to Set:**
```bash
# High error rate
aws cloudwatch put-metric-alarm \
  --alarm-name "EmailWorker-HighErrorRate" \
  --alarm-description "Lambda error rate > 5%" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=FunctionName,Value=email-worker-function

# SES throttling
aws cloudwatch put-metric-alarm \
  --alarm-name "EmailWorker-SESThrottling" \
  --alarm-description "SES throttling detected" \
  --metric-name ThrottleExceptions \
  --namespace EmailWorker/Custom \
  --statistic Sum \
  --period 300 \
  --threshold 1 \
  --comparison-operator GreaterThanThreshold
```

---

## 🧪 **Testing Strategy**

### **1. Start Small:**
```bash
# Test with 100 emails first
python set_lambda_concurrency.py 200
# Send test campaign with 100 emails
# Monitor performance
```

### **2. Scale Up Gradually:**
```bash
# If 100 emails work well, try 1,000
python set_lambda_concurrency.py 400
# Send test campaign with 1,000 emails
# Monitor for SES throttling
```

### **3. Full Scale Test:**
```bash
# If 1,000 emails work well, try 20,000
python set_lambda_concurrency.py 400
# Send full campaign
# Monitor all metrics
```

---

## 🚨 **Troubleshooting**

### **Problem: High Error Rate**
**Symptoms:** Many Lambda errors, emails not being sent
**Solutions:**
1. Reduce concurrency: `python set_lambda_concurrency.py 200`
2. Check Lambda logs: `python view_lambda_errors.py email-worker-function`
3. Increase Lambda memory/timeout

### **Problem: SES Throttling**
**Symptoms:** "Rate exceeded" errors in logs
**Solutions:**
1. Reduce concurrency: `python set_lambda_concurrency.py 200`
2. Request SES limit increase from AWS Support
3. Add more delay between emails in Lambda

### **Problem: Slow Processing**
**Symptoms:** Campaign takes > 30 minutes
**Solutions:**
1. Increase concurrency: `python set_lambda_concurrency.py 600`
2. Increase Lambda memory for better performance
3. Check for bottlenecks in DynamoDB/SES

---

## 💡 **Best Practices**

### **1. Start Conservative:**
- Begin with 200 concurrency
- Test with small campaigns
- Gradually increase based on performance

### **2. Monitor Continuously:**
- Set up CloudWatch alarms
- Check logs regularly
- Monitor SES sending rates

### **3. Have a Rollback Plan:**
- Keep previous concurrency settings noted
- Be ready to reduce concurrency if issues arise
- Test rollback procedures

### **4. Consider Time of Day:**
- Run large campaigns during off-peak hours
- Avoid peak AWS usage times
- Consider timezone of recipients

---

## 📋 **Quick Reference Commands**

```bash
# Set concurrency
python set_lambda_concurrency.py 400

# Check current settings
aws lambda get-function-configuration --function-name email-worker-function

# Monitor in real-time
python tail_lambda_logs.py email-worker-function

# Check for errors
python view_lambda_errors.py email-worker-function 1

# Monitor SQS queue
python check_sqs_status.py
```

---

## 🎯 **Summary for 20,000 Emails**

| **Setting** | **Command** | **Expected Time** | **Risk Level** |
|-------------|-------------|-------------------|----------------|
| **Recommended** | `python set_lambda_concurrency.py 400` | **8-12 minutes** | **Low** |
| **Conservative** | `python set_lambda_concurrency.py 200` | **15-20 minutes** | **Very Low** |
| **Aggressive** | `python set_lambda_concurrency.py 600` | **5-8 minutes** | **Medium** |

**Start with 400, monitor performance, adjust as needed!** 🚀
