import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import csv
import json
import boto3
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import threading
from datetime import datetime
import os

class BulkEmailSender:
    def __init__(self, root):
        self.root = root
        self.root.title("Bulk Email Sender - AWS SES")
        self.root.geometry("1000x700")
        self.root.configure(bg='#f0f0f0')
        
        # Initialize variables
        self.contacts = []
        self.ses_client = None
        self.sending_progress = tk.StringVar(value="Ready")
        
        self.setup_ui()
        self.load_config()
    
    def setup_ui(self):
        # Create notebook for tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Configuration Tab
        self.setup_config_tab(notebook)
        
        # Contacts Tab
        self.setup_contacts_tab(notebook)
        
        # Email Template Tab
        self.setup_template_tab(notebook)
        
        # Send Campaign Tab
        self.setup_campaign_tab(notebook)
        
        # Status bar
        status_frame = tk.Frame(self.root, bg='#e0e0e0', height=30)
        status_frame.pack(fill='x', side='bottom')
        status_label = tk.Label(status_frame, textvariable=self.sending_progress, 
                               bg='#e0e0e0', anchor='w')
        status_label.pack(fill='x', padx=10, pady=5)
    
    def setup_config_tab(self, notebook):
        config_frame = ttk.Frame(notebook)
        notebook.add(config_frame, text="AWS Configuration")
        
        # AWS SES Configuration
        ttk.Label(config_frame, text="AWS SES Configuration", 
                 font=('Arial', 14, 'bold')).pack(pady=10)
        
        # Region
        ttk.Label(config_frame, text="AWS Region:").pack(anchor='w', padx=20)
        self.region_var = tk.StringVar(value="us-east-1")
        region_combo = ttk.Combobox(config_frame, textvariable=self.region_var,
                                   values=["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"])
        region_combo.pack(fill='x', padx=20, pady=5)
        
        # Access Key
        ttk.Label(config_frame, text="AWS Access Key ID:").pack(anchor='w', padx=20, pady=(10,0))
        self.access_key_var = tk.StringVar()
        ttk.Entry(config_frame, textvariable=self.access_key_var, show="*").pack(fill='x', padx=20, pady=5)
        
        # Secret Key
        ttk.Label(config_frame, text="AWS Secret Access Key:").pack(anchor='w', padx=20)
        self.secret_key_var = tk.StringVar()
        ttk.Entry(config_frame, textvariable=self.secret_key_var, show="*").pack(fill='x', padx=20, pady=5)
        
        # From Email
        ttk.Label(config_frame, text="From Email (must be verified in SES):").pack(anchor='w', padx=20, pady=(10,0))
        self.from_email_var = tk.StringVar()
        ttk.Entry(config_frame, textvariable=self.from_email_var).pack(fill='x', padx=20, pady=5)
        
        # Test Connection Button
        ttk.Button(config_frame, text="Test SES Connection", 
                  command=self.test_ses_connection).pack(pady=20)
        
        # Save Config Button
        ttk.Button(config_frame, text="Save Configuration", 
                  command=self.save_config).pack(pady=5)
    
    def setup_contacts_tab(self, notebook):
        contacts_frame = ttk.Frame(notebook)
        notebook.add(contacts_frame, text="Contacts")
        
        # Contacts management
        ttk.Label(contacts_frame, text="Contact Management", 
                 font=('Arial', 14, 'bold')).pack(pady=10)
        
        # Buttons frame
        buttons_frame = tk.Frame(contacts_frame)
        buttons_frame.pack(fill='x', padx=20, pady=10)
        
        ttk.Button(buttons_frame, text="Import CSV", 
                  command=self.import_contacts).pack(side='left', padx=5)
        ttk.Button(buttons_frame, text="Export CSV", 
                  command=self.export_contacts).pack(side='left', padx=5)
        ttk.Button(buttons_frame, text="Add Contact", 
                  command=self.add_contact).pack(side='left', padx=5)
        ttk.Button(buttons_frame, text="Remove Selected", 
                  command=self.remove_contact).pack(side='left', padx=5)
        
        # Contacts list
        columns = ('Email', 'First Name', 'Last Name', 'Company')
        self.contacts_tree = ttk.Treeview(contacts_frame, columns=columns, show='headings', height=15)
        
        for col in columns:
            self.contacts_tree.heading(col, text=col)
            self.contacts_tree.column(col, width=200)
        
        # Scrollbar for contacts list
        scrollbar = ttk.Scrollbar(contacts_frame, orient='vertical', command=self.contacts_tree.yview)
        self.contacts_tree.configure(yscrollcommand=scrollbar.set)
        
        self.contacts_tree.pack(side='left', fill='both', expand=True, padx=20, pady=10)
        scrollbar.pack(side='right', fill='y', pady=10)
    
    def setup_template_tab(self, notebook):
        template_frame = ttk.Frame(notebook)
        notebook.add(template_frame, text="Email Template")
        
        ttk.Label(template_frame, text="Email Template", 
                 font=('Arial', 14, 'bold')).pack(pady=10)
        
        # Subject
        ttk.Label(template_frame, text="Subject:").pack(anchor='w', padx=20)
        self.subject_var = tk.StringVar()
        ttk.Entry(template_frame, textvariable=self.subject_var).pack(fill='x', padx=20, pady=5)
        
        # Email body
        ttk.Label(template_frame, text="Email Body (HTML supported):").pack(anchor='w', padx=20, pady=(10,0))
        self.email_body = scrolledtext.ScrolledText(template_frame, height=20, wrap=tk.WORD)
        self.email_body.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Template buttons
        template_buttons = tk.Frame(template_frame)
        template_buttons.pack(fill='x', padx=20, pady=5)
        
        ttk.Button(template_buttons, text="Load Template", 
                  command=self.load_template).pack(side='left', padx=5)
        ttk.Button(template_buttons, text="Save Template", 
                  command=self.save_template).pack(side='left', padx=5)
        ttk.Button(template_buttons, text="Preview", 
                  command=self.preview_email).pack(side='left', padx=5)
    
    def setup_campaign_tab(self, notebook):
        campaign_frame = ttk.Frame(notebook)
        notebook.add(campaign_frame, text="Send Campaign")
        
        ttk.Label(campaign_frame, text="Send Email Campaign", 
                 font=('Arial', 14, 'bold')).pack(pady=10)
        
        # Campaign settings
        settings_frame = tk.LabelFrame(campaign_frame, text="Campaign Settings", padx=10, pady=10)
        settings_frame.pack(fill='x', padx=20, pady=10)
        
        ttk.Label(settings_frame, text="Campaign Name:").pack(anchor='w')
        self.campaign_name_var = tk.StringVar()
        ttk.Entry(settings_frame, textvariable=self.campaign_name_var).pack(fill='x', pady=5)
        
        # Sending options
        ttk.Label(settings_frame, text="Send Rate (emails per second):").pack(anchor='w', pady=(10,0))
        self.send_rate_var = tk.StringVar(value="1")
        ttk.Entry(settings_frame, textvariable=self.send_rate_var).pack(fill='x', pady=5)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(campaign_frame, variable=self.progress_var, 
                                          maximum=100, length=400)
        self.progress_bar.pack(pady=20)
        
        # Send button
        self.send_button = ttk.Button(campaign_frame, text="Send Campaign", 
                                     command=self.send_campaign, style='Accent.TButton')
        self.send_button.pack(pady=10)
        
        # Results text area
        ttk.Label(campaign_frame, text="Campaign Results:").pack(anchor='w', padx=20, pady=(20,0))
        self.results_text = scrolledtext.ScrolledText(campaign_frame, height=10, wrap=tk.WORD)
        self.results_text.pack(fill='both', expand=True, padx=20, pady=10)
    
    def test_ses_connection(self):
        try:
            self.ses_client = boto3.client(
                'ses',
                region_name=self.region_var.get(),
                aws_access_key_id=self.access_key_var.get(),
                aws_secret_access_key=self.secret_key_var.get()
            )
            
            # Test by getting sending quota
            response = self.ses_client.get_send_quota()
            messagebox.showinfo("Success", 
                              f"SES Connection successful!\nDaily sending quota: {response['Max24HourSend']}")
        except Exception as e:
            messagebox.showerror("Error", f"SES Connection failed: {str(e)}")
    
    def save_config(self):
        config = {
            'region': self.region_var.get(),
            'access_key': self.access_key_var.get(),
            'secret_key': self.secret_key_var.get(),
            'from_email': self.from_email_var.get()
        }
        
        with open('config.json', 'w') as f:
            json.dump(config, f)
        
        messagebox.showinfo("Success", "Configuration saved!")
    
    def load_config(self):
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
            
            self.region_var.set(config.get('region', 'us-east-1'))
            self.access_key_var.set(config.get('access_key', ''))
            self.secret_key_var.set(config.get('secret_key', ''))
            self.from_email_var.set(config.get('from_email', ''))
        except FileNotFoundError:
            pass
    
    def import_contacts(self):
        file_path = filedialog.askopenfilename(
            title="Select CSV file",
            filetypes=[("CSV files", "*.csv")]
        )
        
        if file_path:
            try:
                with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
                    reader = csv.DictReader(csvfile)
                    self.contacts = []
                    
                    for row in reader:
                        contact = {
                            'email': row.get('email', ''),
                            'first_name': row.get('first_name', ''),
                            'last_name': row.get('last_name', ''),
                            'company': row.get('company', '')
                        }
                        self.contacts.append(contact)
                
                self.refresh_contacts_list()
                messagebox.showinfo("Success", f"Imported {len(self.contacts)} contacts!")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to import contacts: {str(e)}")
    
    def export_contacts(self):
        if not self.contacts:
            messagebox.showwarning("Warning", "No contacts to export!")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Save CSV file",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")]
        )
        
        if file_path:
            try:
                with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                    fieldnames = ['email', 'first_name', 'last_name', 'company']
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(self.contacts)
                
                messagebox.showinfo("Success", f"Exported {len(self.contacts)} contacts!")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export contacts: {str(e)}")
    
    def add_contact(self):
        dialog = ContactDialog(self.root)
        if dialog.result:
            self.contacts.append(dialog.result)
            self.refresh_contacts_list()
    
    def remove_contact(self):
        selected = self.contacts_tree.selection()
        if selected:
            item = self.contacts_tree.item(selected[0])
            email = item['values'][0]
            self.contacts = [c for c in self.contacts if c['email'] != email]
            self.refresh_contacts_list()
    
    def refresh_contacts_list(self):
        for item in self.contacts_tree.get_children():
            self.contacts_tree.delete(item)
        
        for contact in self.contacts:
            self.contacts_tree.insert('', 'end', values=(
                contact['email'],
                contact['first_name'],
                contact['last_name'],
                contact['company']
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
            filetypes=[("HTML files", "*.html"), ("Text files", "*.txt")]
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.email_body.get(1.0, tk.END))
                messagebox.showinfo("Success", "Template saved!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save template: {str(e)}")
    
    def preview_email(self):
        if self.contacts:
            sample_contact = self.contacts[0]
            subject = self.personalize_content(self.subject_var.get(), sample_contact)
            body = self.personalize_content(self.email_body.get(1.0, tk.END), sample_contact)
            
            preview_window = tk.Toplevel(self.root)
            preview_window.title("Email Preview")
            preview_window.geometry("600x400")
            
            ttk.Label(preview_window, text=f"Subject: {subject}", 
                     font=('Arial', 12, 'bold')).pack(pady=10)
            
            preview_text = scrolledtext.ScrolledText(preview_window, wrap=tk.WORD)
            preview_text.pack(fill='both', expand=True, padx=10, pady=10)
            preview_text.insert(1.0, body)
            preview_text.config(state='disabled')
    
    def personalize_content(self, content, contact):
        content = content.replace('{{first_name}}', contact.get('first_name', ''))
        content = content.replace('{{last_name}}', contact.get('last_name', ''))
        content = content.replace('{{email}}', contact.get('email', ''))
        content = content.replace('{{company}}', contact.get('company', ''))
        return content
    
    def send_campaign(self):
        if not self.contacts:
            messagebox.showwarning("Warning", "No contacts to send to!")
            return
        
        if not self.subject_var.get().strip():
            messagebox.showwarning("Warning", "Please enter a subject!")
            return
        
        if not self.email_body.get(1.0, tk.END).strip():
            messagebox.showwarning("Warning", "Please enter email content!")
            return
        
        if not self.ses_client:
            messagebox.showwarning("Warning", "Please configure and test SES connection first!")
            return
        
        # Start sending in a separate thread
        self.send_button.config(state='disabled')
        thread = threading.Thread(target=self.send_emails_thread)
        thread.daemon = True
        thread.start()
    
    def send_emails_thread(self):
        total_contacts = len(self.contacts)
        sent_count = 0
        failed_count = 0
        send_rate = float(self.send_rate_var.get())
        
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, f"Starting campaign: {self.campaign_name_var.get()}\n")
        self.results_text.insert(tk.END, f"Total recipients: {total_contacts}\n\n")
        
        for i, contact in enumerate(self.contacts):
            try:
                # Personalize content
                subject = self.personalize_content(self.subject_var.get(), contact)
                body = self.personalize_content(self.email_body.get(1.0, tk.END), contact)
                
                # Send email
                response = self.ses_client.send_email(
                    Source=self.from_email_var.get(),
                    Destination={'ToAddresses': [contact['email']]},
                    Message={
                        'Subject': {'Data': subject},
                        'Body': {'Html': {'Data': body}}
                    }
                )
                
                sent_count += 1
                self.results_text.insert(tk.END, f"✓ Sent to {contact['email']}\n")
                
            except Exception as e:
                failed_count += 1
                self.results_text.insert(tk.END, f"✗ Failed to send to {contact['email']}: {str(e)}\n")
            
            # Update progress
            progress = ((i + 1) / total_contacts) * 100
            self.progress_var.set(progress)
            self.sending_progress.set(f"Sending... {i + 1}/{total_contacts}")
            
            # Rate limiting
            if send_rate > 0:
                import time
                time.sleep(1 / send_rate)
            
            # Update UI
            self.root.update_idletasks()
        
        # Campaign complete
        self.results_text.insert(tk.END, f"\nCampaign completed!\n")
        self.results_text.insert(tk.END, f"Sent: {sent_count}\n")
        self.results_text.insert(tk.END, f"Failed: {failed_count}\n")
        self.results_text.insert(tk.END, f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        self.sending_progress.set("Campaign completed")
        self.send_button.config(state='normal')

class ContactDialog:
    def __init__(self, parent):
        self.result = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Add Contact")
        self.dialog.geometry("400x300")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
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
    app = BulkEmailSender(root)
    root.mainloop()