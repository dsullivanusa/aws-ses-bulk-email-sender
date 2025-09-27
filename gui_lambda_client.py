import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import json
import boto3
import csv
import threading
from datetime import datetime

class LambdaEmailSender:
    def __init__(self, root):
        self.root = root
        self.root.title("Lambda Bulk Email Sender")
        self.root.geometry("1000x700")
        
        self.lambda_client = None
        self.contacts = []
        self.sending_progress = tk.StringVar(value="Ready")
        
        self.setup_ui()
        self.load_config()
    
    def setup_ui(self):
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.setup_config_tab(notebook)
        self.setup_contacts_tab(notebook)
        self.setup_template_tab(notebook)
        self.setup_campaign_tab(notebook)
        
        # Status bar
        status_frame = tk.Frame(self.root, bg='#e0e0e0', height=30)
        status_frame.pack(fill='x', side='bottom')
        status_label = tk.Label(status_frame, textvariable=self.sending_progress, bg='#e0e0e0', anchor='w')
        status_label.pack(fill='x', padx=10, pady=5)
    
    def setup_config_tab(self, notebook):
        config_frame = ttk.Frame(notebook)
        notebook.add(config_frame, text="AWS Configuration")
        
        ttk.Label(config_frame, text="AWS Lambda Configuration", font=('Arial', 14, 'bold')).pack(pady=10)
        
        # Region
        ttk.Label(config_frame, text="AWS Region:").pack(anchor='w', padx=20)
        self.region_var = tk.StringVar(value="us-east-1")
        ttk.Combobox(config_frame, textvariable=self.region_var,
                    values=["us-east-1", "us-west-2", "eu-west-1"]).pack(fill='x', padx=20, pady=5)
        
        # Access Key
        ttk.Label(config_frame, text="AWS Access Key ID:").pack(anchor='w', padx=20, pady=(10,0))
        self.access_key_var = tk.StringVar()
        ttk.Entry(config_frame, textvariable=self.access_key_var, show="*").pack(fill='x', padx=20, pady=5)
        
        # Secret Key
        ttk.Label(config_frame, text="AWS Secret Access Key:").pack(anchor='w', padx=20)
        self.secret_key_var = tk.StringVar()
        ttk.Entry(config_frame, textvariable=self.secret_key_var, show="*").pack(fill='x', padx=20, pady=5)
        
        # Lambda Function Name
        ttk.Label(config_frame, text="Lambda Function Name:").pack(anchor='w', padx=20, pady=(10,0))
        self.lambda_function_var = tk.StringVar(value="email-sender-function")
        ttk.Entry(config_frame, textvariable=self.lambda_function_var).pack(fill='x', padx=20, pady=5)
        
        # From Email
        ttk.Label(config_frame, text="From Email:").pack(anchor='w', padx=20, pady=(10,0))
        self.from_email_var = tk.StringVar()
        ttk.Entry(config_frame, textvariable=self.from_email_var).pack(fill='x', padx=20, pady=5)
        
        ttk.Button(config_frame, text="Test Lambda Connection", command=self.test_lambda_connection).pack(pady=20)
        ttk.Button(config_frame, text="Save Configuration", command=self.save_config).pack(pady=5)
    
    def setup_contacts_tab(self, notebook):
        contacts_frame = ttk.Frame(notebook)
        notebook.add(contacts_frame, text="Contacts (DynamoDB)")
        
        ttk.Label(contacts_frame, text="Contact Management", font=('Arial', 14, 'bold')).pack(pady=10)
        
        # Buttons
        buttons_frame = tk.Frame(contacts_frame)
        buttons_frame.pack(fill='x', padx=20, pady=10)
        
        ttk.Button(buttons_frame, text="Load from DynamoDB", command=self.load_contacts_from_db).pack(side='left', padx=5)
        ttk.Button(buttons_frame, text="Import CSV to DynamoDB", command=self.import_csv_to_db).pack(side='left', padx=5)
        ttk.Button(buttons_frame, text="Add Contact", command=self.add_contact_to_db).pack(side='left', padx=5)
        
        # Contacts list
        columns = ('Email', 'First Name', 'Last Name', 'Company', 'Last Email Sent', 'Email Count')
        self.contacts_tree = ttk.Treeview(contacts_frame, columns=columns, show='headings', height=15)
        
        for col in columns:
            self.contacts_tree.heading(col, text=col)
            self.contacts_tree.column(col, width=150)
        
        scrollbar = ttk.Scrollbar(contacts_frame, orient='vertical', command=self.contacts_tree.yview)
        self.contacts_tree.configure(yscrollcommand=scrollbar.set)
        
        self.contacts_tree.pack(side='left', fill='both', expand=True, padx=20, pady=10)
        scrollbar.pack(side='right', fill='y', pady=10)
    
    def setup_template_tab(self, notebook):
        template_frame = ttk.Frame(notebook)
        notebook.add(template_frame, text="Email Template")
        
        ttk.Label(template_frame, text="Email Template", font=('Arial', 14, 'bold')).pack(pady=10)
        
        # Subject
        ttk.Label(template_frame, text="Subject:").pack(anchor='w', padx=20)
        self.subject_var = tk.StringVar()
        ttk.Entry(template_frame, textvariable=self.subject_var).pack(fill='x', padx=20, pady=5)
        
        # Email body
        ttk.Label(template_frame, text="Email Body (HTML):").pack(anchor='w', padx=20, pady=(10,0))
        self.email_body = scrolledtext.ScrolledText(template_frame, height=20, wrap=tk.WORD)
        self.email_body.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Template buttons
        template_buttons = tk.Frame(template_frame)
        template_buttons.pack(fill='x', padx=20, pady=5)
        
        ttk.Button(template_buttons, text="Load Template", command=self.load_template).pack(side='left', padx=5)
        ttk.Button(template_buttons, text="Save Template", command=self.save_template).pack(side='left', padx=5)
    
    def setup_campaign_tab(self, notebook):
        campaign_frame = ttk.Frame(notebook)
        notebook.add(campaign_frame, text="Send Campaign")
        
        ttk.Label(campaign_frame, text="Send Email Campaign via Lambda", font=('Arial', 14, 'bold')).pack(pady=10)
        
        # Campaign settings
        settings_frame = tk.LabelFrame(campaign_frame, text="Campaign Settings", padx=10, pady=10)
        settings_frame.pack(fill='x', padx=20, pady=10)
        
        ttk.Label(settings_frame, text="Campaign Name:").pack(anchor='w')
        self.campaign_name_var = tk.StringVar()
        ttk.Entry(settings_frame, textvariable=self.campaign_name_var).pack(fill='x', pady=5)
        
        # Send button
        self.send_button = ttk.Button(campaign_frame, text="Send Campaign via Lambda", 
                                     command=self.send_campaign_lambda)
        self.send_button.pack(pady=20)
        
        # Results
        ttk.Label(campaign_frame, text="Campaign Results:").pack(anchor='w', padx=20, pady=(20,0))
        self.results_text = scrolledtext.ScrolledText(campaign_frame, height=15, wrap=tk.WORD)
        self.results_text.pack(fill='both', expand=True, padx=20, pady=10)
    
    def test_lambda_connection(self):
        try:
            self.lambda_client = boto3.client(
                'lambda',
                region_name=self.region_var.get(),
                aws_access_key_id=self.access_key_var.get(),
                aws_secret_access_key=self.secret_key_var.get()
            )
            
            # Test by getting contacts
            response = self.lambda_client.invoke(
                FunctionName=self.lambda_function_var.get(),
                Payload=json.dumps({'action': 'get_contacts'})
            )
            
            messagebox.showinfo("Success", "Lambda connection successful!")
        except Exception as e:
            messagebox.showerror("Error", f"Lambda connection failed: {str(e)}")
    
    def load_contacts_from_db(self):
        if not self.lambda_client:
            messagebox.showwarning("Warning", "Please configure Lambda connection first!")
            return
        
        try:
            response = self.lambda_client.invoke(
                FunctionName=self.lambda_function_var.get(),
                Payload=json.dumps({'action': 'get_contacts'})
            )
            
            result = json.loads(response['Payload'].read())
            body = json.loads(result['body'])
            
            self.contacts = body['contacts']
            self.refresh_contacts_list()
            messagebox.showinfo("Success", f"Loaded {len(self.contacts)} contacts from DynamoDB!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load contacts: {str(e)}")
    
    def import_csv_to_db(self):
        file_path = filedialog.askopenfilename(
            title="Select CSV file",
            filetypes=[("CSV files", "*.csv")]
        )
        
        if file_path and self.lambda_client:
            try:
                with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
                    reader = csv.DictReader(csvfile)
                    
                    for row in reader:
                        contact = {
                            'email': row.get('email', ''),
                            'first_name': row.get('first_name', ''),
                            'last_name': row.get('last_name', ''),
                            'company': row.get('company', '')
                        }
                        
                        # Add to DynamoDB via Lambda
                        self.lambda_client.invoke(
                            FunctionName=self.lambda_function_var.get(),
                            Payload=json.dumps({
                                'action': 'add_contact',
                                'contact': contact
                            })
                        )
                
                messagebox.showinfo("Success", "Contacts imported to DynamoDB!")
                self.load_contacts_from_db()  # Refresh the list
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to import contacts: {str(e)}")
    
    def add_contact_to_db(self):
        dialog = ContactDialog(self.root)
        if dialog.result and self.lambda_client:
            try:
                self.lambda_client.invoke(
                    FunctionName=self.lambda_function_var.get(),
                    Payload=json.dumps({
                        'action': 'add_contact',
                        'contact': dialog.result
                    })
                )
                messagebox.showinfo("Success", "Contact added to DynamoDB!")
                self.load_contacts_from_db()  # Refresh the list
            except Exception as e:
                messagebox.showerror("Error", f"Failed to add contact: {str(e)}")
    
    def send_campaign_lambda(self):
        if not self.lambda_client:
            messagebox.showwarning("Warning", "Please configure Lambda connection first!")
            return
        
        if not self.subject_var.get().strip():
            messagebox.showwarning("Warning", "Please enter a subject!")
            return
        
        if not self.email_body.get(1.0, tk.END).strip():
            messagebox.showwarning("Warning", "Please enter email content!")
            return
        
        self.send_button.config(state='disabled')
        thread = threading.Thread(target=self.send_campaign_thread)
        thread.daemon = True
        thread.start()
    
    def send_campaign_thread(self):
        try:
            payload = {
                'action': 'send_campaign',
                'subject': self.subject_var.get(),
                'body': self.email_body.get(1.0, tk.END),
                'from_email': self.from_email_var.get(),
                'campaign_name': self.campaign_name_var.get()
            }
            
            self.sending_progress.set("Sending campaign via Lambda...")
            
            response = self.lambda_client.invoke(
                FunctionName=self.lambda_function_var.get(),
                Payload=json.dumps(payload)
            )
            
            result = json.loads(response['Payload'].read())
            body = json.loads(result['body'])
            
            # Display results
            self.results_text.delete(1.0, tk.END)
            self.results_text.insert(tk.END, f"Campaign: {body['campaign_name']}\n")
            self.results_text.insert(tk.END, f"Total Contacts: {body['total_contacts']}\n")
            self.results_text.insert(tk.END, f"Sent: {body['sent_count']}\n")
            self.results_text.insert(tk.END, f"Failed: {body['failed_count']}\n")
            self.results_text.insert(tk.END, f"Timestamp: {body['timestamp']}\n\n")
            
            for result in body['results']:
                status_icon = "✓" if result['status'] == 'sent' else "✗"
                self.results_text.insert(tk.END, f"{status_icon} {result['email']} - {result['status']}\n")
            
            self.sending_progress.set("Campaign completed")
            
        except Exception as e:
            self.results_text.delete(1.0, tk.END)
            self.results_text.insert(tk.END, f"Error: {str(e)}")
            self.sending_progress.set("Campaign failed")
        
        finally:
            self.send_button.config(state='normal')
            self.load_contacts_from_db()  # Refresh to show updated email counts
    
    def refresh_contacts_list(self):
        for item in self.contacts_tree.get_children():
            self.contacts_tree.delete(item)
        
        for contact in self.contacts:
            self.contacts_tree.insert('', 'end', values=(
                contact.get('email', ''),
                contact.get('first_name', ''),
                contact.get('last_name', ''),
                contact.get('company', ''),
                contact.get('last_email_sent', 'Never'),
                contact.get('email_count', 0)
            ))
    
    def load_template(self):
        file_path = filedialog.askopenfilename(
            title="Select template file",
            filetypes=[("HTML files", "*.html"), ("Text files", "*.txt")]
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.email_body.delete(1.0, tk.END)
                self.email_body.insert(1.0, content)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load template: {str(e)}")
    
    def save_template(self):
        file_path = filedialog.asksaveasfilename(
            title="Save template",
            defaultextension=".html",
            filetypes=[("HTML files", "*.html")]
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.email_body.get(1.0, tk.END))
                messagebox.showinfo("Success", "Template saved!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save template: {str(e)}")
    
    def save_config(self):
        config = {
            'region': self.region_var.get(),
            'access_key': self.access_key_var.get(),
            'secret_key': self.secret_key_var.get(),
            'lambda_function': self.lambda_function_var.get(),
            'from_email': self.from_email_var.get()
        }
        
        with open('lambda_config.json', 'w') as f:
            json.dump(config, f)
        
        messagebox.showinfo("Success", "Configuration saved!")
    
    def load_config(self):
        try:
            with open('lambda_config.json', 'r') as f:
                config = json.load(f)
            
            self.region_var.set(config.get('region', 'us-east-1'))
            self.access_key_var.set(config.get('access_key', ''))
            self.secret_key_var.set(config.get('secret_key', ''))
            self.lambda_function_var.set(config.get('lambda_function', 'email-sender-function'))
            self.from_email_var.set(config.get('from_email', ''))
        except FileNotFoundError:
            pass

class ContactDialog:
    def __init__(self, parent):
        self.result = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Add Contact")
        self.dialog.geometry("400x300")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Create form
        ttk.Label(self.dialog, text="Email:").pack(anchor='w', padx=20, pady=(20,5))
        self.email_var = tk.StringVar()
        ttk.Entry(self.dialog, textvariable=self.email_var).pack(fill='x', padx=20, pady=5)
        
        ttk.Label(self.dialog, text="First Name:").pack(anchor='w', padx=20, pady=(10,5))
        self.first_name_var = tk.StringVar()
        ttk.Entry(self.dialog, textvariable=self.first_name_var).pack(fill='x', padx=20, pady=5)
        
        ttk.Label(self.dialog, text="Last Name:").pack(anchor='w', padx=20, pady=(10,5))
        self.last_name_var = tk.StringVar()
        ttk.Entry(self.dialog, textvariable=self.last_name_var).pack(fill='x', padx=20, pady=5)
        
        ttk.Label(self.dialog, text="Company:").pack(anchor='w', padx=20, pady=(10,5))
        self.company_var = tk.StringVar()
        ttk.Entry(self.dialog, textvariable=self.company_var).pack(fill='x', padx=20, pady=5)
        
        # Buttons
        button_frame = tk.Frame(self.dialog)
        button_frame.pack(pady=20)
        
        ttk.Button(button_frame, text="Add", command=self.add_contact).pack(side='left', padx=10)
        ttk.Button(button_frame, text="Cancel", command=self.dialog.destroy).pack(side='left', padx=10)
    
    def add_contact(self):
        if self.email_var.get().strip():
            self.result = {
                'email': self.email_var.get().strip(),
                'first_name': self.first_name_var.get().strip(),
                'last_name': self.last_name_var.get().strip(),
                'company': self.company_var.get().strip()
            }
            self.dialog.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = LambdaEmailSender(root)
    root.mainloop()