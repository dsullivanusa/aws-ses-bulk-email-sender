#!/usr/bin/env python3
"""
Campaign Tracking GUI - Visual Campaign Analytics Tool
Track campaigns, view recipients, export reports
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import boto3
from decimal import Decimal
import json
from datetime import datetime
import csv

class DecimalEncoder(json.JSONEncoder):
    """Handle Decimal types"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

class CampaignTrackingGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("📊 Campaign Tracking - Analytics Dashboard")
        self.root.geometry("1400x900")
        self.root.resizable(True, True)
        
        # Variables
        self.campaigns = []
        self.selected_campaign = None
        self.region = 'us-gov-west-1'
        
        # Setup UI
        self.setup_ui()
        
        # Load campaigns
        self.load_campaigns()
    
    def setup_ui(self):
        """Setup the main UI"""
        # Main container
        main_container = ttk.Frame(self.root, padding="10")
        main_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_container.columnconfigure(0, weight=1)
        main_container.rowconfigure(2, weight=1)
        
        # Header
        self.create_header(main_container)
        
        # Toolbar
        self.create_toolbar(main_container)
        
        # Campaign list (top half)
        list_frame = ttk.LabelFrame(main_container, text="📋 Campaigns", padding="10")
        list_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        # Treeview with scrollbars
        tree_container = ttk.Frame(list_frame)
        tree_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        tree_container.columnconfigure(0, weight=1)
        tree_container.rowconfigure(0, weight=1)
        
        vsb = ttk.Scrollbar(tree_container, orient="vertical")
        hsb = ttk.Scrollbar(tree_container, orient="horizontal")
        
        self.tree = ttk.Treeview(tree_container, yscrollcommand=vsb.set, xscrollcommand=hsb.set,
                                 height=15)
        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)
        
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        vsb.grid(row=0, column=1, sticky=(tk.N, tk.S))
        hsb.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # Configure columns
        self.tree['columns'] = ('name', 'launched_by', 'created_at', 'sent_at', 'status', 
                                'total', 'sent', 'failed')
        self.tree['show'] = 'tree headings'
        
        self.tree.heading('#0', text='Campaign ID')
        self.tree.heading('name', text='Campaign Name')
        self.tree.heading('launched_by', text='Launched By')
        self.tree.heading('created_at', text='Created')
        self.tree.heading('sent_at', text='Sent At')
        self.tree.heading('status', text='Status')
        self.tree.heading('total', text='Total')
        self.tree.heading('sent', text='Sent')
        self.tree.heading('failed', text='Failed')
        
        self.tree.column('#0', width=150, anchor='w')
        self.tree.column('name', width=200, anchor='w')
        self.tree.column('launched_by', width=180, anchor='w')
        self.tree.column('created_at', width=140, anchor='center')
        self.tree.column('sent_at', width=140, anchor='center')
        self.tree.column('status', width=100, anchor='center')
        self.tree.column('total', width=60, anchor='center')
        self.tree.column('sent', width=60, anchor='center')
        self.tree.column('failed', width=60, anchor='center')
        
        # Bind selection
        self.tree.bind('<<TreeviewSelect>>', self.on_campaign_select)
        
        # Details panel (bottom half)
        detail_frame = ttk.LabelFrame(main_container, text="📝 Campaign Details", padding="10")
        detail_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        detail_frame.columnconfigure(0, weight=1)
        detail_frame.rowconfigure(1, weight=1)
        
        # Detail tabs
        self.detail_notebook = ttk.Notebook(detail_frame)
        self.detail_notebook.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Summary tab
        summary_tab = ttk.Frame(self.detail_notebook, padding="10")
        self.detail_notebook.add(summary_tab, text="📊 Summary")
        
        summary_tab.columnconfigure(0, weight=1)
        summary_tab.rowconfigure(0, weight=1)
        
        self.summary_text = scrolledtext.ScrolledText(summary_tab, height=10, wrap=tk.WORD,
                                                      font=('Consolas', 10))
        self.summary_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Recipients tab
        recipients_tab = ttk.Frame(self.detail_notebook, padding="10")
        self.detail_notebook.add(recipients_tab, text="📧 Recipients")
        
        recipients_tab.columnconfigure(0, weight=1)
        recipients_tab.rowconfigure(0, weight=1)
        
        self.recipients_text = scrolledtext.ScrolledText(recipients_tab, height=10, wrap=tk.WORD,
                                                         font=('Consolas', 10))
        self.recipients_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # JSON tab
        json_tab = ttk.Frame(self.detail_notebook, padding="10")
        self.detail_notebook.add(json_tab, text="🔧 Raw JSON")
        
        json_tab.columnconfigure(0, weight=1)
        json_tab.rowconfigure(0, weight=1)
        
        self.json_text = scrolledtext.ScrolledText(json_tab, height=10, wrap=tk.WORD,
                                                   font=('Consolas', 9))
        self.json_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Status bar
        self.create_status_bar(main_container)
    
    def create_header(self, parent):
        """Create header with title and region selector"""
        header_frame = ttk.Frame(parent)
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        header_frame.columnconfigure(1, weight=1)
        
        ttk.Label(header_frame, text="📊 Campaign Tracking Dashboard", 
                 font=('Arial', 16, 'bold')).grid(row=0, column=0, columnspan=3, pady=(0, 5))
        
        ttk.Label(header_frame, text="Region:", font=('Arial', 9, 'bold')).grid(
            row=1, column=0, sticky=tk.W, padx=(0, 5))
        
        self.region_var = tk.StringVar(value=self.region)
        region_combo = ttk.Combobox(header_frame, textvariable=self.region_var,
                                    values=['us-gov-west-1', 'us-east-1', 'us-west-2'],
                                    width=20, state='readonly')
        region_combo.grid(row=1, column=1, sticky=tk.W)
        region_combo.bind('<<ComboboxSelected>>', lambda e: self.load_campaigns())
        
        self.campaign_count_label = ttk.Label(header_frame, text="Campaigns: 0",
                                             font=('Arial', 10, 'bold'))
        self.campaign_count_label.grid(row=1, column=2, padx=20)
    
    def create_toolbar(self, parent):
        """Create toolbar with action buttons"""
        toolbar = ttk.Frame(parent)
        toolbar.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Button(toolbar, text="🔄 Refresh", 
                  command=self.load_campaigns).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(toolbar, text="📥 Export Campaign to CSV", 
                  command=self.export_campaign).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(toolbar, text="📧 Export Email List Only", 
                  command=self.export_email_list_only).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(toolbar, text="📊 Export All to CSV", 
                  command=self.export_all_campaigns).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(toolbar, text="🔍 Filter by Status", 
                  command=self.filter_by_status).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(toolbar, text="🗑️ Clear Filter", 
                  command=self.clear_filter).pack(side=tk.LEFT, padx=5)
        
        # Search box
        ttk.Label(toolbar, text="Search:").pack(side=tk.LEFT, padx=(20, 5))
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(toolbar, textvariable=self.search_var, width=25)
        search_entry.pack(side=tk.LEFT, padx=5)
        search_entry.bind('<KeyRelease>', lambda e: self.search_campaigns())
    
    def create_status_bar(self, parent):
        """Create status bar"""
        status_frame = ttk.Frame(parent)
        status_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(status_frame, textvariable=self.status_var,
                                relief=tk.SUNKEN, anchor=tk.W)
        status_label.pack(fill=tk.X)
    
    def load_campaigns(self):
        """Load campaigns from DynamoDB"""
        try:
            self.region = self.region_var.get()
            self.status_var.set("Loading campaigns...")
            self.root.update_idletasks()
            
            dynamodb = boto3.resource('dynamodb', region_name=self.region)
            campaigns_table = dynamodb.Table('EmailCampaigns')
            
            response = campaigns_table.scan()
            campaigns = response.get('Items', [])
            
            # Handle pagination
            while 'LastEvaluatedKey' in response:
                response = campaigns_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
                campaigns.extend(response.get('Items', []))
            
            self.campaigns = sorted(campaigns, key=lambda x: x.get('created_at', ''), reverse=True)
            self.display_campaigns(self.campaigns)
            
            self.campaign_count_label.config(text=f"Campaigns: {len(self.campaigns)}")
            self.status_var.set(f"Loaded {len(self.campaigns)} campaigns from {self.region}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load campaigns:\n{str(e)}")
            self.status_var.set("Error loading campaigns")
    
    def display_campaigns(self, campaigns):
        """Display campaigns in treeview"""
        # Clear existing
        self.tree.delete(*self.tree.get_children())
        
        if not campaigns:
            self.status_var.set("No campaigns to display")
            return
        
        # Insert campaigns
        for campaign in campaigns:
            campaign_id = campaign.get('campaign_id', 'N/A')
            name = campaign.get('campaign_name', 'N/A')
            launched_by = campaign.get('launched_by', 'Unknown')[:25]
            created_at = campaign.get('created_at', 'N/A')
            if created_at != 'N/A':
                try:
                    dt = datetime.fromisoformat(created_at)
                    created_at = dt.strftime('%Y-%m-%d %H:%M')
                except:
                    pass
            
            sent_at = campaign.get('sent_at', 'Not sent')
            if sent_at and sent_at != 'Not sent':
                try:
                    dt = datetime.fromisoformat(sent_at)
                    sent_at = dt.strftime('%Y-%m-%d %H:%M')
                except:
                    pass
            
            status = campaign.get('status', 'unknown')
            total = campaign.get('total_contacts', 0)
            sent = campaign.get('sent_count', 0)
            failed = campaign.get('failed_count', 0)
            
            self.tree.insert('', 'end', text=campaign_id,
                           values=(name, launched_by, created_at, sent_at, status, total, sent, failed))
    
    def on_campaign_select(self, event):
        """Handle campaign selection"""
        selection = self.tree.selection()
        if not selection:
            return
        
        # Get campaign ID
        campaign_id = self.tree.item(selection[0])['text']
        
        # Find campaign in list
        self.selected_campaign = next((c for c in self.campaigns if c.get('campaign_id') == campaign_id), None)
        
        if self.selected_campaign:
            self.display_campaign_details()
    
    def display_campaign_details(self):
        """Display detailed information about selected campaign"""
        if not self.selected_campaign:
            return
        
        # Summary
        summary_lines = [
            "="*80,
            "CAMPAIGN SUMMARY",
            "="*80,
            f"Campaign ID:       {self.selected_campaign.get('campaign_id', 'N/A')}",
            f"Campaign Name:     {self.selected_campaign.get('campaign_name', 'N/A')}",
            f"Launched By:       {self.selected_campaign.get('launched_by', 'Unknown')}",
            f"",
            f"Created At:        {self.selected_campaign.get('created_at', 'N/A')}",
            f"Sent At:           {self.selected_campaign.get('sent_at', 'Not yet sent')}",
            f"Status:            {self.selected_campaign.get('status', 'unknown')}",
            f"",
            f"Subject:           {self.selected_campaign.get('subject', 'N/A')}",
            f"From Email:        {self.selected_campaign.get('from_email', 'N/A')}",
            f"",
            "-"*80,
            "STATISTICS",
            "-"*80,
            f"Filter:            {self.selected_campaign.get('filter_description', 'No filter')}",
            f"Total Contacts:    {self.selected_campaign.get('total_contacts', 0)}",
            f"Successfully Sent: {self.selected_campaign.get('sent_count', 0)}",
            f"Failed:            {self.selected_campaign.get('failed_count', 0)}",
            ""
        ]
        
        attachments = self.selected_campaign.get('attachments', [])
        if attachments:
            summary_lines.append("-"*80)
            summary_lines.append(f"ATTACHMENTS ({len(attachments)})")
            summary_lines.append("-"*80)
            for att in attachments:
                summary_lines.append(f"  • {att.get('filename', 'unknown')} ({att.get('size', 0)} bytes)")
            summary_lines.append("")
        
        self.summary_text.delete(1.0, tk.END)
        self.summary_text.insert(1.0, '\n'.join(summary_lines))
        
        # Recipients
        recipients = self.selected_campaign.get('target_contacts', [])
        recipient_lines = [
            "="*80,
            f"RECIPIENT EMAIL ADDRESSES ({len(recipients)} total)",
            "="*80,
            ""
        ]
        
        if recipients:
            for idx, email in enumerate(recipients, 1):
                recipient_lines.append(f"  {idx:4d}. {email}")
        else:
            recipient_lines.append("  No email addresses recorded")
        
        self.recipients_text.delete(1.0, tk.END)
        self.recipients_text.insert(1.0, '\n'.join(recipient_lines))
        
        # Raw JSON
        json_str = json.dumps(self.selected_campaign, indent=2, cls=DecimalEncoder)
        self.json_text.delete(1.0, tk.END)
        self.json_text.insert(1.0, json_str)
    
    def export_campaign(self):
        """Export selected campaign to CSV"""
        if not self.selected_campaign:
            messagebox.showwarning("No Selection", "Please select a campaign first")
            return
        
        campaign_id = self.selected_campaign.get('campaign_id', 'unknown')
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"campaign_{campaign_id}_recipients.csv"
        )
        
        if not filename:
            return
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Header with metadata
                writer.writerow(['Campaign Report'])
                writer.writerow(['Campaign ID', self.selected_campaign.get('campaign_id', 'N/A')])
                writer.writerow(['Campaign Name', self.selected_campaign.get('campaign_name', 'N/A')])
                writer.writerow(['Launched By', self.selected_campaign.get('launched_by', 'Unknown')])
                writer.writerow(['Created At', self.selected_campaign.get('created_at', 'N/A')])
                writer.writerow(['Sent At', self.selected_campaign.get('sent_at', 'Not sent')])
                writer.writerow(['Status', self.selected_campaign.get('status', 'unknown')])
                writer.writerow(['Total Recipients', self.selected_campaign.get('total_contacts', 0)])
                writer.writerow(['Successfully Sent', self.selected_campaign.get('sent_count', 0)])
                writer.writerow(['Failed', self.selected_campaign.get('failed_count', 0)])
                writer.writerow([])
                
                # Recipient list
                writer.writerow(['Recipient Email Addresses'])
                writer.writerow(['#', 'Email Address'])
                
                recipients = self.selected_campaign.get('target_contacts', [])
                for idx, email in enumerate(recipients, 1):
                    writer.writerow([idx, email])
            
            messagebox.showinfo("Success", f"Exported to:\n{filename}")
            self.status_var.set(f"Exported campaign to {filename}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Export failed:\n{str(e)}")
    
    def export_email_list_only(self):
        """Export just the email addresses list to CSV"""
        if not self.selected_campaign:
            messagebox.showwarning("No Selection", "Please select a campaign first")
            return
        
        campaign_id = self.selected_campaign.get('campaign_id', 'unknown')
        campaign_name = self.selected_campaign.get('campaign_name', 'campaign')
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"campaign_{campaign_id}_email_list.csv"
        )
        
        if not filename:
            return
        
        try:
            recipients = self.selected_campaign.get('target_contacts', [])
            
            if not recipients:
                messagebox.showwarning("No Recipients", "This campaign has no email addresses recorded")
                return
            
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Simple header
                writer.writerow([f'Email Addresses for Campaign: {campaign_name}'])
                writer.writerow([f'Campaign ID: {campaign_id}'])
                writer.writerow([f'Total Recipients: {len(recipients)}'])
                writer.writerow([f'Exported: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'])
                writer.writerow([])  # Blank row
                
                # Column header
                writer.writerow(['Email Address'])
                
                # Email addresses only (one per row)
                for email in recipients:
                    writer.writerow([email])
            
            messagebox.showinfo("Success", 
                f"Exported {len(recipients)} email addresses to:\n{filename}")
            self.status_var.set(f"Exported {len(recipients)} email addresses")
            
        except Exception as e:
            messagebox.showerror("Error", f"Export failed:\n{str(e)}")
    
    def export_all_campaigns(self):
        """Export all campaigns summary to CSV"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"all_campaigns_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        
        if not filename:
            return
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Header
                writer.writerow([
                    'Campaign ID',
                    'Campaign Name',
                    'Launched By',
                    'Created At',
                    'Sent At',
                    'Status',
                    'Filter Description',
                    'Total Contacts',
                    'Successfully Sent',
                    'Failed',
                    'Recipient Count'
                ])
                
                # Data
                for campaign in self.campaigns:
                    writer.writerow([
                        campaign.get('campaign_id', 'N/A'),
                        campaign.get('campaign_name', 'N/A'),
                        campaign.get('launched_by', 'Unknown'),
                        campaign.get('created_at', 'N/A'),
                        campaign.get('sent_at', 'Not sent'),
                        campaign.get('status', 'unknown'),
                        campaign.get('filter_description', 'No filter'),
                        campaign.get('total_contacts', 0),
                        campaign.get('sent_count', 0),
                        campaign.get('failed_count', 0),
                        len(campaign.get('target_contacts', []))
                    ])
            
            messagebox.showinfo("Success", f"Exported {len(self.campaigns)} campaigns to:\n{filename}")
            self.status_var.set(f"Exported all campaigns to {filename}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Export failed:\n{str(e)}")
    
    def filter_by_status(self):
        """Filter campaigns by status"""
        status = tk.simpledialog.askstring("Filter by Status",
                                          "Enter status (queued/sending/completed/failed):",
                                          parent=self.root)
        
        if status:
            filtered = [c for c in self.campaigns if c.get('status', '').lower() == status.lower()]
            self.display_campaigns(filtered)
            self.status_var.set(f"Showing {len(filtered)} campaigns with status '{status}'")
    
    def clear_filter(self):
        """Clear all filters"""
        self.search_var.set('')
        self.display_campaigns(self.campaigns)
        self.status_var.set(f"Showing all {len(self.campaigns)} campaigns")
    
    def search_campaigns(self):
        """Search campaigns by name"""
        search_term = self.search_var.get().lower()
        
        if not search_term:
            self.display_campaigns(self.campaigns)
            return
        
        filtered = [c for c in self.campaigns if search_term in c.get('campaign_name', '').lower()]
        self.display_campaigns(filtered)
        self.status_var.set(f"Found {len(filtered)} matching campaigns")

def main():
    root = tk.Tk()
    app = CampaignTrackingGUI(root)
    root.mainloop()

if __name__ == '__main__':
    import tkinter.simpledialog
    main()

