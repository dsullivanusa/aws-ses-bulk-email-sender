import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import csv
import json
import threading
from datetime import datetime
from smtp_email_sender import SMTPEmailSender

class SMTPBulkEmailSender:
    def __init__(self, root):
        self.root = root
        self.root.title("SMTP Bulk Email Sender")
        self.root.geometry("1000x700")
        
        self.contacts = []
        self.attachments = []
        self.sending_progress = tk.StringVar(value="Ready")
        
        self.setup_ui()
        self.load_config()
    
    def setup_ui(self):
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.setup_smtp_config_tab(notebook)
        self.setup_contacts_tab(notebook)
        self.setup_template_tab(notebook)
        self.setup_campaign_tab(notebook)
        
        # Status bar
        status_frame = tk.Frame(self.root, bg='#e0e0e0', height=30)
        status_frame.pack(fill='x', side='bottom')
        status_label = tk.Label(status_frame, textvariable=self.sending_progress, bg='#e0e0e0', anchor='w')
        status_label.pack(fill='x', padx=10, pady=5)
    
    def setup_smtp_config_tab(self, notebook):
        config_frame = ttk.Frame(notebook)
        notebook.add(config_frame, text="SMTP Configuration")
        
        ttk.Label(config_frame, text="SMTP Server Configuration", font=('Arial', 14, 'bold')).pack(pady=10)
        
        # SMTP Server
        ttk.Label(config_frame, text="SMTP Server:").pack(anchor='w', padx=20)
        self.smtp_server_var = tk.StringVar(value="smtp.gmail.com")
        ttk.Entry(config_frame, textvariable=self.smtp_server_var).pack(fill='x', padx=20, pady=5)
        
        # Port
        ttk.Label(config_frame, text="Port:").pack(anchor='w', padx=20, pady=(10,0))
        self.smtp_port_var = tk.StringVar(value="587")
        ttk.Entry(config_frame, textvariable=self.smtp_port_var).pack(fill='x', padx=20, pady=5)
        
        # Username
        ttk.Label(config_frame, text="Username:").pack(anchor='w', padx=20, pady=(10,0))
        self.smtp_username_var = tk.StringVar()
        ttk.Entry(config_frame, textvariable=self.smtp_username_var).pack(fill='x', padx=20, pady=5)
        
        # Password
        ttk.Label(config_frame, text="Password:").pack(anchor='w', padx=20, pady=(10,0))
        self.smtp_password_var = tk.StringVar()
        ttk.Entry(config_frame, textvariable=self.smtp_password_var, show="*").pack(fill='x', padx=20, pady=5)
        
        # From Email
        ttk.Label(config_frame, text="From Email:").pack(anchor='w', padx=20, pady=(10,0))
        self.from_email_var = tk.StringVar()
        ttk.Entry(config_frame, textvariable=self.from_email_var).pack(fill='x', padx=20, pady=5)
        
        # TLS
        self.use_tls_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(config_frame, text="Use TLS", variable=self.use_tls_var).pack(anchor='w', padx=20, pady=10)
        
        ttk.Button(config_frame, text="Test SMTP Connection", command=self.test_smtp_connection).pack(pady=20)
        ttk.Button(config_frame, text="Save Configuration", command=self.save_config).pack(pady=5)
    
    def setup_contacts_tab(self, notebook):
        contacts_frame = ttk.Frame(notebook)
        notebook.add(contacts_frame, text="Contacts")
        
        ttk.Label(contacts_frame, text="Contact Management", font=('Arial', 14, 'bold')).pack(pady=10)
        
        # Buttons
        buttons_frame = tk.Frame(contacts_frame)
        buttons_frame.pack(fill='x', padx=20, pady=10)
        
        ttk.Button(buttons_frame, text="Import CSV", command=self.import_contacts).pack(side='left', padx=5)
        ttk.Button(buttons_frame, text="Export CSV", command=self.export_contacts).pack(side='left', padx=5)
        ttk.Button(buttons_frame, text="Add Contact", command=self.add_contact).pack(side='left', padx=5)
        
        # Contacts list
        columns = ('Email', 'First Name', 'Last Name', 'Company')
        self.contacts_tree = ttk.Treeview(contacts_frame, columns=columns, show='headings', height=15)
        
        for col in columns:
            self.contacts_tree.heading(col, text=col)
            self.contacts_tree.column(col, width=200)
        
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
        self.email_body = scrolledtext.ScrolledText(template_frame, height=15, wrap=tk.WORD)
        self.email_body.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Attachments
        ttk.Label(template_frame, text="Attachments:").pack(anchor='w', padx=20)
        
        attachments_frame = tk.Frame(template_frame)
        attachments_frame.pack(fill='x', padx=20, pady=5)
        
        ttk.Button(attachments_frame, text="Add Attachment", command=self.add_attachment).pack(side='left', padx=5)
        ttk.Button(attachments_frame, text="Clear Attachments", command=self.clear_attachments).pack(side='left', padx=5)
        
        self.attachments_listbox = tk.Listbox(template_frame, height=4)
        self.attachments_listbox.pack(fill='x', padx=20, pady=5)
    
    def setup_campaign_tab(self, notebook):
        campaign_frame = ttk.Frame(notebook)
        notebook.add(campaign_frame, text="Send Campaign")
        
        ttk.Label(campaign_frame, text="Send Email Campaign", font=('Arial', 14, 'bold')).pack(pady=10)
        
        # Campaign settings
        settings_frame = tk.LabelFrame(campaign_frame, text="Campaign Settings", padx=10, pady=10)
        settings_frame.pack(fill='x', padx=20, pady=10)
        
        ttk.Label(settings_frame, text="Campaign Name:").pack(anchor='w')
        self.campaign_name_var = tk.StringVar()
        ttk.Entry(settings_frame, textvariable=self.campaign_name_var).pack(fill='x', pady=5)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(campaign_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill='x', padx=20, pady=20)
        
        # Send button
        self.send_button = ttk.Button(campaign_frame, text="Send Campaign", command=self.send_campaign)
        self.send_button.pack(pady=10)
        
        # Results
        ttk.Label(campaign_frame, text="Campaign Results:").pack(anchor='w', padx=20, pady=(20,0))
        self.results_text = scrolledtext.ScrolledText(campaign_frame, height=10, wrap=tk.WORD)
        self.results_text.pack(fill='both', expand=True, padx=20, pady=10)
    
    def test_smtp_connection(self):
        try:
            smtp_config = {
                'server': self.smtp_server_var.get(),
                'port': int(self.smtp_port_var.get()),
                'username': self.smtp_username_var.get(),
                'password': self.smtp_password_var.get(),
                'use_tls': self.use_tls_var.get()
            }
            
            sender = SMTPEmailSender(smtp_config)
            success, error = sender.send_email(
                self.from_email_var.get(),
                self.from_email_var.get(),
                "Test Email",
                "This is a test email from SMTP Bulk Email Sender."
            )
            
            if success:
                messagebox.showinfo("Success", "SMTP connection successful!")
            else:
                messagebox.showerror("Error", f"SMTP connection failed: {error}")
                
        except Exception as e:
            messagebox.showerror("Error", f"SMTP connection failed: {str(e)}")
    
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
    
    def add_attachment(self):
        file_path = filedialog.askopenfilename(
            title="Select attachment",
            filetypes=[("All files", "*.*")]
        )
        
        if file_path:
            self.attachments.append(file_path)
            self.attachments_listbox.insert(tk.END, file_path)
    
    def clear_attachments(self):
        self.attachments = []
        self.attachments_listbox.delete(0, tk.END)
    
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
        
        self.send_button.config(state='disabled')
        thread = threading.Thread(target=self.send_campaign_thread)
        thread.daemon = True
        thread.start()
    
    def send_campaign_thread(self):
        try:
            smtp_config = {
                'server': self.smtp_server_var.get(),
                'port': int(self.smtp_port_var.get()),
                'username': self.smtp_username_var.get(),
                'password': self.smtp_password_var.get(),
                'use_tls': self.use_tls_var.get()
            }
            
            sender = SMTPEmailSender(smtp_config)
            
            self.sending_progress.set("Sending campaign...")
            
            results = sender.send_bulk_campaign(
                from_email=self.from_email_var.get(),
                contacts=self.contacts,
                subject=self.subject_var.get(),
                body=self.email_body.get(1.0, tk.END),
                attachments=self.attachments if self.attachments else None
            )
            
            # Display results
            sent_count = sum(1 for r in results if r['status'] == 'sent')
            failed_count = len(results) - sent_count
            
            self.results_text.delete(1.0, tk.END)
            self.results_text.insert(tk.END, f"Campaign: {self.campaign_name_var.get()}\n")
            self.results_text.insert(tk.END, f"Total Contacts: {len(self.contacts)}\n")
            self.results_text.insert(tk.END, f"Sent: {sent_count}\n")
            self.results_text.insert(tk.END, f"Failed: {failed_count}\n")
            self.results_text.insert(tk.END, f"Attachments: {len(self.attachments)}\n\n")
            
            for result in results:
                status_icon = "✓" if result['status'] == 'sent' else "✗"
                self.results_text.insert(tk.END, f"{status_icon} {result['email']} - {result['status']}\n")
            
            self.sending_progress.set("Campaign completed")
            
        except Exception as e:
            self.results_text.delete(1.0, tk.END)
            self.results_text.insert(tk.END, f"Error: {str(e)}")
            self.sending_progress.set("Campaign failed")
        
        finally:
            self.send_button.config(state='normal')
    
    def save_config(self):
        config = {
            'smtp_server': self.smtp_server_var.get(),
            'smtp_port': self.smtp_port_var.get(),
            'smtp_username': self.smtp_username_var.get(),
            'smtp_password': self.smtp_password_var.get(),
            'from_email': self.from_email_var.get(),
            'use_tls': self.use_tls_var.get()
        }
        
        with open('smtp_config.json', 'w') as f:
            json.dump(config, f)
        
        messagebox.showinfo("Success", "Configuration saved!")
    
    def load_config(self):
        try:
            with open('smtp_config.json', 'r') as f:
                config = json.load(f)
            
            self.smtp_server_var.set(config.get('smtp_server', 'smtp.gmail.com'))
            self.smtp_port_var.set(config.get('smtp_port', '587'))
            self.smtp_username_var.set(config.get('smtp_username', ''))
            self.smtp_password_var.set(config.get('smtp_password', ''))
            self.from_email_var.set(config.get('from_email', ''))
            self.use_tls_var.set(config.get('use_tls', True))
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
    app = SMTPBulkEmailSender(root)
    root.mainloop()