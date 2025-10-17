#!/usr/bin/env python3
"""
GUI Application to Generate Test Contacts for Load Testing
Creates contacts with same email but unique IDs in DynamoDB
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import boto3
import uuid
from datetime import datetime
import time
import threading

class TestContactGeneratorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🧪 Test Contact Generator - Load Testing Tool")
        self.root.geometry("900x950")
        self.root.resizable(True, True)
        
        # Variables
        self.is_running = False
        self.cancel_requested = False
        
        # Configure style
        style = ttk.Style()
        style.theme_use('clam')
        
        # Main container with padding
        main_frame = ttk.Frame(root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="🧪 Test Contact Generator", 
                               font=('Arial', 18, 'bold'))
        title_label.grid(row=0, column=0, pady=(0, 10))
        
        subtitle_label = ttk.Label(main_frame, text="Generate duplicate contacts for load testing",
                                   font=('Arial', 10))
        subtitle_label.grid(row=1, column=0, pady=(0, 20))
        
        # Configuration Section
        config_frame = ttk.LabelFrame(main_frame, text="📋 Configuration", padding="15")
        config_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        config_frame.columnconfigure(1, weight=1)
        
        # AWS Configuration
        row = 0
        ttk.Label(config_frame, text="AWS Region:", font=('Arial', 9, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=5)
        self.region_var = tk.StringVar(value='us-gov-west-1')
        region_entry = ttk.Entry(config_frame, textvariable=self.region_var, width=30)
        region_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=5)
        
        row += 1
        ttk.Label(config_frame, text="DynamoDB Table:", font=('Arial', 9, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=5)
        self.table_var = tk.StringVar(value='EmailContacts')
        table_entry = ttk.Entry(config_frame, textvariable=self.table_var, width=30)
        table_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=5)
        
        row += 1
        ttk.Label(config_frame, text="Test Email:", font=('Arial', 9, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=5)
        self.email_var = tk.StringVar(value='test@example.com')
        email_entry = ttk.Entry(config_frame, textvariable=self.email_var, width=30)
        email_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=5)
        
        row += 1
        ttk.Label(config_frame, text="Number of Contacts:", font=('Arial', 9, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=5)
        self.count_var = tk.StringVar(value='10000')
        count_entry = ttk.Entry(config_frame, textvariable=self.count_var, width=30)
        count_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=5)
        
        # Contact Template Section
        template_frame = ttk.LabelFrame(main_frame, text="👤 Contact Template", padding="15")
        template_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        template_frame.columnconfigure(1, weight=1)
        template_frame.columnconfigure(3, weight=1)
        
        # Template fields in 2 columns
        fields = [
            ('First Name:', 'first_name_var', 'Test'),
            ('Last Name:', 'last_name_var', 'User'),
            ('Title:', 'title_var', 'IT Director'),
            ('Entity Type:', 'entity_type_var', 'State Government'),
            ('State:', 'state_var', 'CA'),
            ('Agency Name:', 'agency_var', 'Test Agency'),
            ('Sector:', 'sector_var', 'Government'),
            ('Subsection:', 'subsection_var', 'IT Services'),
            ('Phone:', 'phone_var', '555-0100'),
            ('Region:', 'region_contact_var', 'West'),
        ]
        
        row = 0
        for i, (label, var_name, default) in enumerate(fields):
            col = (i % 2) * 2
            row_num = i // 2
            
            ttk.Label(template_frame, text=label).grid(
                row=row_num, column=col, sticky=tk.W, pady=3, padx=(0, 5))
            setattr(self, var_name, tk.StringVar(value=default))
            entry = ttk.Entry(template_frame, textvariable=getattr(self, var_name), width=20)
            entry.grid(row=row_num, column=col+1, sticky=(tk.W, tk.E), pady=3, padx=(0, 15))
        
        # Boolean fields
        bool_frame = ttk.LabelFrame(main_frame, text="✅ Contact Flags", padding="15")
        bool_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        
        bool_fields = [
            ('MS-ISAC Member', 'ms_isac_var', True),
            ('SOC Call', 'soc_call_var', True),
            ('Fusion Center', 'fusion_center_var', False),
            ('K-12', 'k12_var', False),
            ('Water/Wastewater', 'water_wastewater_var', False),
            ('Weekly Rollup', 'weekly_rollup_var', True),
        ]
        
        for i, (label, var_name, default) in enumerate(bool_fields):
            setattr(self, var_name, tk.BooleanVar(value=default))
            cb = ttk.Checkbutton(bool_frame, text=label, variable=getattr(self, var_name))
            cb.grid(row=i//3, column=i%3, sticky=tk.W, padx=15, pady=5)
        
        # Progress Section
        progress_frame = ttk.LabelFrame(main_frame, text="📊 Progress", padding="15")
        progress_frame.grid(row=5, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        progress_frame.columnconfigure(0, weight=1)
        
        # Progress bar
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var,
                                           maximum=100, length=400, mode='determinate')
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Status label
        self.status_var = tk.StringVar(value='Ready to generate test contacts')
        status_label = ttk.Label(progress_frame, textvariable=self.status_var,
                                font=('Arial', 10))
        status_label.grid(row=1, column=0, pady=(0, 5))
        
        # Statistics
        stats_frame = ttk.Frame(progress_frame)
        stats_frame.grid(row=2, column=0, pady=(5, 0))
        stats_frame.columnconfigure((0, 1, 2, 3), weight=1)
        
        ttk.Label(stats_frame, text="Imported:", font=('Arial', 9)).grid(row=0, column=0, padx=10)
        self.imported_var = tk.StringVar(value='0')
        ttk.Label(stats_frame, textvariable=self.imported_var, 
                 font=('Arial', 11, 'bold'), foreground='green').grid(row=1, column=0, padx=10)
        
        ttk.Label(stats_frame, text="Rate:", font=('Arial', 9)).grid(row=0, column=1, padx=10)
        self.rate_var = tk.StringVar(value='0/sec')
        ttk.Label(stats_frame, textvariable=self.rate_var,
                 font=('Arial', 11, 'bold'), foreground='blue').grid(row=1, column=1, padx=10)
        
        ttk.Label(stats_frame, text="ETA:", font=('Arial', 9)).grid(row=0, column=2, padx=10)
        self.eta_var = tk.StringVar(value='--')
        ttk.Label(stats_frame, textvariable=self.eta_var,
                 font=('Arial', 11, 'bold'), foreground='orange').grid(row=1, column=2, padx=10)
        
        ttk.Label(stats_frame, text="Errors:", font=('Arial', 9)).grid(row=0, column=3, padx=10)
        self.errors_var = tk.StringVar(value='0')
        ttk.Label(stats_frame, textvariable=self.errors_var,
                 font=('Arial', 11, 'bold'), foreground='red').grid(row=1, column=3, padx=10)
        
        # Log Section
        log_frame = ttk.LabelFrame(main_frame, text="📝 Log", padding="10")
        log_frame.grid(row=6, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 15))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(6, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, wrap=tk.WORD,
                                                  font=('Consolas', 9))
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=7, column=0, pady=(0, 0))
        
        self.start_button = ttk.Button(button_frame, text="🚀 Start Generation",
                                       command=self.start_generation)
        self.start_button.grid(row=0, column=0, padx=5)
        
        self.cancel_button = ttk.Button(button_frame, text="🛑 Cancel",
                                        command=self.cancel_generation, state='disabled')
        self.cancel_button.grid(row=0, column=1, padx=5)
        
        ttk.Button(button_frame, text="🗑️ Clear Log",
                  command=self.clear_log).grid(row=0, column=2, padx=5)
        
        ttk.Button(button_frame, text="❌ Exit",
                  command=self.root.quit).grid(row=0, column=3, padx=5)
        
        self.log("Application started. Configure settings and click 'Start Generation'")
    
    def log(self, message):
        """Add message to log with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def clear_log(self):
        """Clear the log"""
        self.log_text.delete(1.0, tk.END)
        self.log("Log cleared")
    
    def update_progress(self, current, total, rate, eta, errors):
        """Update progress bar and statistics"""
        progress_pct = (current / total * 100) if total > 0 else 0
        self.progress_var.set(progress_pct)
        self.imported_var.set(f"{current:,}")
        self.rate_var.set(f"{rate:.1f}/sec")
        self.eta_var.set(f"{eta:.0f}s" if eta > 0 else "Done")
        self.errors_var.set(str(errors))
        self.root.update_idletasks()
    
    def validate_inputs(self):
        """Validate user inputs"""
        try:
            count = int(self.count_var.get())
            if count <= 0:
                raise ValueError("Count must be positive")
            if count > 100000:
                if not messagebox.askyesno("Warning", 
                    f"You're about to generate {count:,} contacts. This may take a long time. Continue?"):
                    return False
        except ValueError:
            messagebox.showerror("Invalid Input", "Number of contacts must be a positive integer")
            return False
        
        if not self.email_var.get().strip():
            messagebox.showerror("Invalid Input", "Test email is required")
            return False
        
        if not self.table_var.get().strip():
            messagebox.showerror("Invalid Input", "Table name is required")
            return False
        
        return True
    
    def start_generation(self):
        """Start the contact generation process"""
        if not self.validate_inputs():
            return
        
        # Confirm action
        count = int(self.count_var.get())
        table = self.table_var.get()
        
        if not messagebox.askyesno("Confirm", 
            f"Generate {count:,} test contacts in table '{table}'?\n\n"
            f"This will create contacts with:\n"
            f"• Same email: {self.email_var.get()}\n"
            f"• Unique contact IDs\n"
            f"• Same contact data\n\n"
            f"Continue?"):
            return
        
        # Disable start button, enable cancel
        self.start_button.config(state='disabled')
        self.cancel_button.config(state='normal')
        self.is_running = True
        self.cancel_requested = False
        
        # Reset progress
        self.progress_var.set(0)
        self.imported_var.set('0')
        self.rate_var.set('0/sec')
        self.eta_var.set('--')
        self.errors_var.set('0')
        
        # Start generation in separate thread
        thread = threading.Thread(target=self.generate_contacts)
        thread.daemon = True
        thread.start()
    
    def cancel_generation(self):
        """Cancel the generation process"""
        if messagebox.askyesno("Cancel", "Are you sure you want to cancel?"):
            self.cancel_requested = True
            self.log("⚠️ Cancellation requested...")
            self.cancel_button.config(state='disabled')
    
    def generate_contacts(self):
        """Main generation logic (runs in separate thread)"""
        try:
            # Get configuration
            region = self.region_var.get()
            table_name = self.table_var.get()
            test_email = self.email_var.get()
            total_contacts = int(self.count_var.get())
            
            # Build contact template
            contact_template = {
                'email': test_email,
                'first_name': self.first_name_var.get(),
                'last_name': self.last_name_var.get(),
                'title': self.title_var.get(),
                'entity_type': self.entity_type_var.get(),
                'state': self.state_var.get(),
                'agency_name': self.agency_var.get(),
                'sector': self.sector_var.get(),
                'subsection': self.subsection_var.get(),
                'phone': self.phone_var.get(),
                'ms_isac_member': 'Yes' if self.ms_isac_var.get() else 'No',
                'soc_call': 'Yes' if self.soc_call_var.get() else 'No',
                'fusion_center': 'Yes' if self.fusion_center_var.get() else 'No',
                'k12': 'Yes' if self.k12_var.get() else 'No',
                'water_wastewater': 'Yes' if self.water_wastewater_var.get() else 'No',
                'weekly_rollup': 'Yes' if self.weekly_rollup_var.get() else 'No',
                'alternate_email': f"alt.{test_email}",
                'region': self.region_contact_var.get(),
                'created_at': datetime.now().isoformat()
            }
            
            self.log("="*70)
            self.log(f"🚀 Starting generation of {total_contacts:,} test contacts")
            self.log(f"📊 Table: {table_name}")
            self.log(f"📧 Email: {test_email}")
            self.log(f"👤 Name: {contact_template['first_name']} {contact_template['last_name']}")
            self.log("="*70)
            
            # Connect to DynamoDB
            self.status_var.set("Connecting to DynamoDB...")
            dynamodb = boto3.resource('dynamodb', region_name=region)
            table = dynamodb.Table(table_name)
            
            self.log(f"✅ Connected to DynamoDB table: {table_name}")
            
            total_imported = 0
            total_errors = 0
            BATCH_SIZE = 25
            
            start_time = time.time()
            self.status_var.set("Generating contacts...")
            
            # Process in batches
            with table.batch_writer() as batch:
                for i in range(total_contacts):
                    if self.cancel_requested:
                        self.log("❌ Generation cancelled by user")
                        break
                    
                    # Create contact with unique ID
                    contact = contact_template.copy()
                    contact['contact_id'] = str(uuid.uuid4())
                    
                    try:
                        batch.put_item(Item=contact)
                        total_imported += 1
                        
                        # Update progress every 100 contacts
                        if (i + 1) % 100 == 0:
                            elapsed = time.time() - start_time
                            rate = (i + 1) / elapsed
                            remaining = (total_contacts - (i + 1)) / rate if rate > 0 else 0
                            
                            self.update_progress(i + 1, total_contacts, rate, remaining, total_errors)
                        
                        # Log milestone
                        if (i + 1) % 1000 == 0:
                            elapsed = time.time() - start_time
                            rate = (i + 1) / elapsed
                            self.log(f"✓ Progress: {i+1:,}/{total_contacts:,} "
                                   f"({(i+1)/total_contacts*100:.1f}%) - {rate:.1f} contacts/sec")
                    
                    except Exception as e:
                        total_errors += 1
                        if total_errors <= 5:
                            self.log(f"❌ Error: {str(e)}")
            
            # Final update
            end_time = time.time()
            duration = end_time - start_time
            
            if not self.cancel_requested:
                self.update_progress(total_imported, total_contacts, 
                                   total_imported/duration if duration > 0 else 0, 
                                   0, total_errors)
                
                self.log("="*70)
                self.log("✅ GENERATION COMPLETE!")
                self.log("="*70)
                self.log(f"📊 Total Contacts Created: {total_imported:,}")
                self.log(f"❌ Errors: {total_errors}")
                self.log(f"⏱️  Duration: {duration:.1f}s ({duration/60:.1f} minutes)")
                self.log(f"⚡ Rate: {total_imported/duration:.1f} contacts/second")
                self.log("")
                self.log(f"✨ All contacts have unique contact_id but same email: {test_email}")
                self.log("🧪 Ready for load testing!")
                
                self.status_var.set("✅ Generation completed successfully!")
                
                messagebox.showinfo("Success", 
                    f"Successfully generated {total_imported:,} test contacts!\n\n"
                    f"Duration: {duration/60:.1f} minutes\n"
                    f"Rate: {total_imported/duration:.1f} contacts/sec")
            else:
                self.status_var.set("❌ Generation cancelled")
                self.log(f"⚠️ Partial completion: {total_imported:,} contacts created before cancellation")
        
        except Exception as e:
            self.log(f"❌ ERROR: {str(e)}")
            self.status_var.set(f"❌ Error: {str(e)}")
            messagebox.showerror("Error", f"Generation failed:\n{str(e)}")
        
        finally:
            # Re-enable buttons
            self.start_button.config(state='normal')
            self.cancel_button.config(state='disabled')
            self.is_running = False

def main():
    root = tk.Tk()
    app = TestContactGeneratorGUI(root)
    root.mainloop()

if __name__ == '__main__':
    main()

