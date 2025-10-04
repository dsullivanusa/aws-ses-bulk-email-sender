#!/usr/bin/env python3
"""
DynamoDB Manager GUI - Comprehensive Database Management Tool
Query, Update, and Delete data across all project tables
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import boto3
from boto3.dynamodb.conditions import Key, Attr
import json
from datetime import datetime
from decimal import Decimal
import csv

class DecimalEncoder(json.JSONEncoder):
    """Handle Decimal types in JSON serialization"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

class DynamoDBManagerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🗄️ DynamoDB Manager - Database Administration Tool")
        self.root.geometry("1400x900")
        self.root.resizable(True, True)
        
        # Variables
        self.current_table = None
        self.current_data = []
        self.selected_item = None
        self.table_schema = {}
        
        # AWS Configuration
        self.region = 'us-gov-west-1'
        self.dynamodb = None
        
        # Project tables
        self.project_tables = [
            'EmailContacts',
            'EmailContactsNew',
            'EmailCampaigns',
            'EmailConfig',
            'SMTPConfig'
        ]
        
        # Setup UI
        self.setup_ui()
        
        # Connect to DynamoDB
        self.connect_dynamodb()
    
    def setup_ui(self):
        """Setup the main UI"""
        # Main container
        main_container = ttk.Frame(self.root, padding="10")
        main_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_container.columnconfigure(0, weight=1)
        main_container.rowconfigure(1, weight=1)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_container)
        self.notebook.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Header
        self.create_header(main_container)
        
        # Create tabs
        self.create_browse_tab()
        self.create_query_tab()
        self.create_edit_tab()
        self.create_bulk_tab()
        
        # Status bar
        self.create_status_bar(main_container)
    
    def create_header(self, parent):
        """Create header with connection info"""
        header_frame = ttk.Frame(parent)
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        header_frame.columnconfigure(1, weight=1)
        
        # Title
        ttk.Label(header_frame, text="🗄️ DynamoDB Manager", 
                 font=('Arial', 16, 'bold')).grid(row=0, column=0, columnspan=3, pady=(0, 5))
        
        # Region
        ttk.Label(header_frame, text="Region:", font=('Arial', 9, 'bold')).grid(
            row=1, column=0, sticky=tk.W, padx=(0, 5))
        self.region_var = tk.StringVar(value=self.region)
        region_combo = ttk.Combobox(header_frame, textvariable=self.region_var, 
                                    values=['us-gov-west-1', 'us-east-1', 'us-west-2'], 
                                    width=20, state='readonly')
        region_combo.grid(row=1, column=1, sticky=tk.W, padx=(0, 20))
        region_combo.bind('<<ComboboxSelected>>', lambda e: self.connect_dynamodb())
        
        # Table selection
        ttk.Label(header_frame, text="Table:", font=('Arial', 9, 'bold')).grid(
            row=1, column=2, sticky=tk.W, padx=(0, 5))
        self.table_var = tk.StringVar()
        self.table_combo = ttk.Combobox(header_frame, textvariable=self.table_var, 
                                        values=self.project_tables, width=25, state='readonly')
        self.table_combo.grid(row=1, column=3, sticky=tk.W, padx=(0, 20))
        self.table_combo.bind('<<ComboboxSelected>>', self.on_table_selected)
        
        # Refresh button
        ttk.Button(header_frame, text="🔄 Refresh Tables", 
                  command=self.refresh_tables).grid(row=1, column=4, padx=5)
        
        # Connection status
        self.connection_status = ttk.Label(header_frame, text="⚪ Not Connected", 
                                          foreground='gray')
        self.connection_status.grid(row=1, column=5, padx=20)
    
    def create_browse_tab(self):
        """Create browse/view tab"""
        browse_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(browse_frame, text="📊 Browse Data")
        
        browse_frame.columnconfigure(0, weight=1)
        browse_frame.rowconfigure(1, weight=1)
        
        # Toolbar
        toolbar = ttk.Frame(browse_frame)
        toolbar.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Button(toolbar, text="🔄 Load All Records", 
                  command=self.load_all_records).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="🗑️ Delete Selected", 
                  command=self.delete_selected_record).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="✏️ Edit Selected", 
                  command=self.edit_selected_record).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="📥 Export to CSV", 
                  command=self.export_to_csv).pack(side=tk.LEFT, padx=5)
        
        self.record_count_label = ttk.Label(toolbar, text="Records: 0")
        self.record_count_label.pack(side=tk.RIGHT, padx=10)
        
        # Search frame
        search_frame = ttk.LabelFrame(browse_frame, text="🔍 Quick Search", padding="10")
        search_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(search_frame, text="Search Field:").pack(side=tk.LEFT, padx=5)
        self.search_field_var = tk.StringVar()
        self.search_field_combo = ttk.Combobox(search_frame, textvariable=self.search_field_var,
                                               width=20, state='readonly')
        self.search_field_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(search_frame, text="Value:").pack(side=tk.LEFT, padx=5)
        self.search_value_var = tk.StringVar()
        ttk.Entry(search_frame, textvariable=self.search_value_var, width=30).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(search_frame, text="🔍 Search", 
                  command=self.quick_search).pack(side=tk.LEFT, padx=5)
        ttk.Button(search_frame, text="❌ Clear", 
                  command=self.clear_search).pack(side=tk.LEFT, padx=5)
        
        # Treeview with scrollbars
        tree_frame = ttk.Frame(browse_frame)
        tree_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        
        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")
        
        # Treeview
        self.tree = ttk.Treeview(tree_frame, yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)
        
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        vsb.grid(row=0, column=1, sticky=(tk.N, tk.S))
        hsb.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # Bind selection event
        self.tree.bind('<<TreeviewSelect>>', self.on_tree_select)
        
        # Detail view
        detail_frame = ttk.LabelFrame(browse_frame, text="📝 Record Details", padding="10")
        detail_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        detail_frame.columnconfigure(0, weight=1)
        
        self.detail_text = scrolledtext.ScrolledText(detail_frame, height=8, wrap=tk.WORD,
                                                     font=('Consolas', 9))
        self.detail_text.grid(row=0, column=0, sticky=(tk.W, tk.E))
    
    def create_query_tab(self):
        """Create advanced query tab"""
        query_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(query_frame, text="🔎 Advanced Query")
        
        query_frame.columnconfigure(0, weight=1)
        query_frame.rowconfigure(2, weight=1)
        
        # Query builder
        builder_frame = ttk.LabelFrame(query_frame, text="🛠️ Query Builder", padding="10")
        builder_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        builder_frame.columnconfigure(1, weight=1)
        
        # Key condition
        ttk.Label(builder_frame, text="Primary Key:", font=('Arial', 9, 'bold')).grid(
            row=0, column=0, sticky=tk.W, pady=5)
        self.pk_name_var = tk.StringVar()
        ttk.Entry(builder_frame, textvariable=self.pk_name_var, width=20).grid(
            row=0, column=1, sticky=tk.W, padx=5)
        ttk.Label(builder_frame, text="=").grid(row=0, column=2, padx=5)
        self.pk_value_var = tk.StringVar()
        ttk.Entry(builder_frame, textvariable=self.pk_value_var, width=30).grid(
            row=0, column=3, sticky=(tk.W, tk.E), padx=5)
        
        # Filter condition
        ttk.Label(builder_frame, text="Filter Attribute:", font=('Arial', 9, 'bold')).grid(
            row=1, column=0, sticky=tk.W, pady=5)
        self.filter_attr_var = tk.StringVar()
        ttk.Entry(builder_frame, textvariable=self.filter_attr_var, width=20).grid(
            row=1, column=1, sticky=tk.W, padx=5)
        
        self.filter_op_var = tk.StringVar(value='=')
        ttk.Combobox(builder_frame, textvariable=self.filter_op_var,
                    values=['=', '!=', '<', '<=', '>', '>=', 'contains', 'begins_with'],
                    width=12, state='readonly').grid(row=1, column=2, padx=5)
        
        self.filter_value_var = tk.StringVar()
        ttk.Entry(builder_frame, textvariable=self.filter_value_var, width=30).grid(
            row=1, column=3, sticky=(tk.W, tk.E), padx=5)
        
        # Query buttons
        button_frame = ttk.Frame(builder_frame)
        button_frame.grid(row=2, column=0, columnspan=4, pady=10)
        
        ttk.Button(button_frame, text="🔍 Execute Query", 
                  command=self.execute_query).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="📊 Scan Table", 
                  command=self.scan_table).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="❌ Clear Query", 
                  command=self.clear_query).pack(side=tk.LEFT, padx=5)
        
        # Raw query option
        raw_frame = ttk.LabelFrame(query_frame, text="📝 Raw Query (Advanced)", padding="10")
        raw_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        raw_frame.columnconfigure(0, weight=1)
        
        ttk.Label(raw_frame, text="Enter custom filter expression:").grid(row=0, column=0, sticky=tk.W)
        self.raw_query_text = scrolledtext.ScrolledText(raw_frame, height=4, wrap=tk.WORD,
                                                        font=('Consolas', 9))
        self.raw_query_text.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Button(raw_frame, text="▶️ Execute Raw Query", 
                  command=self.execute_raw_query).grid(row=2, column=0)
        
        # Results
        results_frame = ttk.LabelFrame(query_frame, text="📊 Query Results", padding="10")
        results_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)
        
        self.query_results_text = scrolledtext.ScrolledText(results_frame, wrap=tk.WORD,
                                                           font=('Consolas', 9))
        self.query_results_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    
    def create_edit_tab(self):
        """Create edit/update tab"""
        edit_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(edit_frame, text="✏️ Edit Record")
        
        edit_frame.columnconfigure(0, weight=1)
        edit_frame.rowconfigure(1, weight=1)
        
        # Info
        info_label = ttk.Label(edit_frame, 
                              text="Select a record from Browse tab or enter key below to edit",
                              font=('Arial', 9, 'italic'))
        info_label.grid(row=0, column=0, pady=(0, 10))
        
        # Key input
        key_frame = ttk.LabelFrame(edit_frame, text="🔑 Record Identifier", padding="10")
        key_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        key_frame.columnconfigure(1, weight=1)
        
        ttk.Label(key_frame, text="Primary Key Name:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.edit_pk_name_var = tk.StringVar()
        ttk.Entry(key_frame, textvariable=self.edit_pk_name_var, width=25).grid(
            row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        
        ttk.Label(key_frame, text="Primary Key Value:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.edit_pk_value_var = tk.StringVar()
        ttk.Entry(key_frame, textvariable=self.edit_pk_value_var, width=25).grid(
            row=1, column=1, sticky=(tk.W, tk.E), padx=5)
        
        ttk.Button(key_frame, text="🔍 Load Record", 
                  command=self.load_record_for_edit).grid(row=2, column=0, columnspan=2, pady=10)
        
        # Edit area
        edit_area_frame = ttk.LabelFrame(edit_frame, text="📝 Edit JSON", padding="10")
        edit_area_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        edit_area_frame.columnconfigure(0, weight=1)
        edit_area_frame.rowconfigure(0, weight=1)
        
        self.edit_text = scrolledtext.ScrolledText(edit_area_frame, wrap=tk.WORD,
                                                   font=('Consolas', 10))
        self.edit_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Buttons
        edit_buttons = ttk.Frame(edit_frame)
        edit_buttons.grid(row=3, column=0, pady=(0, 10))
        
        ttk.Button(edit_buttons, text="💾 Save Changes", 
                  command=self.save_record).pack(side=tk.LEFT, padx=5)
        ttk.Button(edit_buttons, text="❌ Cancel", 
                  command=self.cancel_edit).pack(side=tk.LEFT, padx=5)
        ttk.Button(edit_buttons, text="✅ Validate JSON", 
                  command=self.validate_json).pack(side=tk.LEFT, padx=5)
    
    def create_bulk_tab(self):
        """Create bulk operations tab"""
        bulk_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(bulk_frame, text="⚡ Bulk Operations")
        
        bulk_frame.columnconfigure(0, weight=1)
        
        # Warning
        warning_frame = ttk.Frame(bulk_frame)
        warning_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        warning_frame.configure(relief='solid', borderwidth=2)
        
        warning_label = ttk.Label(warning_frame, 
                                 text="⚠️ Warning: Bulk operations affect multiple records. Use with caution!",
                                 font=('Arial', 10, 'bold'), foreground='red')
        warning_label.pack(pady=10)
        
        # Bulk delete
        delete_frame = ttk.LabelFrame(bulk_frame, text="🗑️ Bulk Delete", padding="15")
        delete_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        
        ttk.Label(delete_frame, text="Delete all records matching filter:").pack(anchor=tk.W, pady=5)
        
        filter_frame = ttk.Frame(delete_frame)
        filter_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(filter_frame, text="Attribute:").pack(side=tk.LEFT, padx=5)
        self.bulk_attr_var = tk.StringVar()
        ttk.Entry(filter_frame, textvariable=self.bulk_attr_var, width=20).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(filter_frame, text="=").pack(side=tk.LEFT, padx=5)
        self.bulk_value_var = tk.StringVar()
        ttk.Entry(filter_frame, textvariable=self.bulk_value_var, width=30).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(delete_frame, text="🗑️ Execute Bulk Delete", 
                  command=self.bulk_delete).pack(pady=10)
        
        # Bulk export
        export_frame = ttk.LabelFrame(bulk_frame, text="📤 Export Table", padding="15")
        export_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        
        ttk.Label(export_frame, text="Export entire table to JSON or CSV").pack(anchor=tk.W, pady=5)
        
        export_buttons = ttk.Frame(export_frame)
        export_buttons.pack(pady=10)
        
        ttk.Button(export_buttons, text="📥 Export to JSON", 
                  command=lambda: self.export_table('json')).pack(side=tk.LEFT, padx=5)
        ttk.Button(export_buttons, text="📥 Export to CSV", 
                  command=lambda: self.export_table('csv')).pack(side=tk.LEFT, padx=5)
        
        # Table info
        info_frame = ttk.LabelFrame(bulk_frame, text="ℹ️ Table Information", padding="15")
        info_frame.grid(row=3, column=0, sticky=(tk.W, tk.E))
        
        self.table_info_text = scrolledtext.ScrolledText(info_frame, height=10, wrap=tk.WORD,
                                                        font=('Consolas', 9))
        self.table_info_text.pack(fill=tk.BOTH, expand=True)
        
        ttk.Button(info_frame, text="🔄 Refresh Table Info", 
                  command=self.refresh_table_info).pack(pady=5)
    
    def create_status_bar(self, parent):
        """Create status bar"""
        status_frame = ttk.Frame(parent)
        status_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(status_frame, textvariable=self.status_var, 
                                relief=tk.SUNKEN, anchor=tk.W)
        status_label.pack(fill=tk.X)
    
    def connect_dynamodb(self):
        """Connect to DynamoDB"""
        try:
            self.region = self.region_var.get()
            self.dynamodb = boto3.resource('dynamodb', region_name=self.region)
            self.connection_status.config(text="🟢 Connected", foreground='green')
            self.status_var.set(f"Connected to DynamoDB in {self.region}")
            self.refresh_tables()
        except Exception as e:
            self.connection_status.config(text="🔴 Connection Failed", foreground='red')
            messagebox.showerror("Connection Error", f"Failed to connect to DynamoDB:\n{str(e)}")
    
    def refresh_tables(self):
        """Refresh available tables"""
        try:
            client = boto3.client('dynamodb', region_name=self.region)
            response = client.list_tables()
            tables = response.get('TableNames', [])
            
            # Filter for project tables
            available_tables = [t for t in tables if any(pt in t for pt in self.project_tables)]
            
            self.table_combo['values'] = available_tables
            self.status_var.set(f"Found {len(available_tables)} project tables")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to list tables:\n{str(e)}")
    
    def on_table_selected(self, event=None):
        """Handle table selection"""
        table_name = self.table_var.get()
        if table_name:
            self.current_table = table_name
            self.status_var.set(f"Selected table: {table_name}")
            self.get_table_schema()
            self.update_search_fields()
    
    def get_table_schema(self):
        """Get table schema/key information"""
        try:
            client = boto3.client('dynamodb', region_name=self.region)
            response = client.describe_table(TableName=self.current_table)
            
            table_info = response['Table']
            key_schema = table_info['KeySchema']
            
            self.table_schema = {
                'keys': [k['AttributeName'] for k in key_schema],
                'key_types': {k['AttributeName']: k['KeyType'] for k in key_schema}
            }
            
            # Update query tab with primary key
            if self.table_schema['keys']:
                self.pk_name_var.set(self.table_schema['keys'][0])
                self.edit_pk_name_var.set(self.table_schema['keys'][0])
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to get table schema:\n{str(e)}")
    
    def update_search_fields(self):
        """Update search field dropdown"""
        if self.current_table:
            # Get sample item to determine fields
            try:
                table = self.dynamodb.Table(self.current_table)
                response = table.scan(Limit=1)
                
                if response.get('Items'):
                    fields = list(response['Items'][0].keys())
                    self.search_field_combo['values'] = fields
                    if fields:
                        self.search_field_var.set(fields[0])
            except:
                pass
    
    def load_all_records(self):
        """Load all records from current table"""
        if not self.current_table:
            messagebox.showwarning("No Table", "Please select a table first")
            return
        
        try:
            self.status_var.set("Loading records...")
            self.root.update_idletasks()
            
            table = self.dynamodb.Table(self.current_table)
            response = table.scan()
            items = response.get('Items', [])
            
            # Handle pagination
            while 'LastEvaluatedKey' in response:
                response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
                items.extend(response.get('Items', []))
            
            self.current_data = items
            self.display_data(items)
            self.record_count_label.config(text=f"Records: {len(items)}")
            self.status_var.set(f"Loaded {len(items)} records from {self.current_table}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load records:\n{str(e)}")
            self.status_var.set("Error loading records")
    
    def display_data(self, items):
        """Display data in treeview"""
        # Clear existing
        self.tree.delete(*self.tree.get_children())
        
        if not items:
            self.status_var.set("No records to display")
            return
        
        # Get all unique columns
        columns = set()
        for item in items:
            columns.update(item.keys())
        columns = sorted(list(columns))
        
        # Configure treeview
        self.tree['columns'] = columns
        self.tree['show'] = 'tree headings'
        
        # Column headers
        self.tree.heading('#0', text='#')
        self.tree.column('#0', width=50, anchor='center')
        
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=150, anchor='w')
        
        # Insert data
        for idx, item in enumerate(items, 1):
            values = []
            for col in columns:
                value = item.get(col, '')
                # Convert to string, handle special types
                if isinstance(value, (dict, list)):
                    value = json.dumps(value, cls=DecimalEncoder)
                elif isinstance(value, Decimal):
                    value = float(value)
                values.append(str(value))
            
            self.tree.insert('', 'end', text=str(idx), values=values, tags=(idx-1,))
    
    def on_tree_select(self, event):
        """Handle treeview selection"""
        selection = self.tree.selection()
        if selection:
            item_id = self.tree.item(selection[0])['tags'][0]
            self.selected_item = self.current_data[item_id]
            
            # Display in detail view
            self.detail_text.delete(1.0, tk.END)
            self.detail_text.insert(1.0, json.dumps(self.selected_item, indent=2, cls=DecimalEncoder))
    
    def quick_search(self):
        """Quick search in current data"""
        if not self.current_data:
            messagebox.showinfo("No Data", "Load records first")
            return
        
        field = self.search_field_var.get()
        value = self.search_value_var.get()
        
        if not field or not value:
            messagebox.showwarning("Invalid Search", "Please enter both field and value")
            return
        
        # Filter data
        results = [item for item in self.current_data 
                  if str(item.get(field, '')).lower().find(value.lower()) >= 0]
        
        self.display_data(results)
        self.status_var.set(f"Found {len(results)} matching records")
    
    def clear_search(self):
        """Clear search and show all data"""
        self.search_value_var.set('')
        if self.current_data:
            self.display_data(self.current_data)
            self.status_var.set(f"Showing all {len(self.current_data)} records")
    
    def delete_selected_record(self):
        """Delete selected record"""
        if not self.selected_item:
            messagebox.showwarning("No Selection", "Please select a record to delete")
            return
        
        if not messagebox.askyesno("Confirm Delete", 
            f"Are you sure you want to delete this record?\n\n"
            f"{json.dumps(self.selected_item, indent=2, cls=DecimalEncoder)[:200]}..."):
            return
        
        try:
            table = self.dynamodb.Table(self.current_table)
            
            # Build key from schema
            key = {}
            for key_name in self.table_schema['keys']:
                key[key_name] = self.selected_item[key_name]
            
            table.delete_item(Key=key)
            
            messagebox.showinfo("Success", "Record deleted successfully")
            self.load_all_records()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete record:\n{str(e)}")
    
    def edit_selected_record(self):
        """Load selected record into edit tab"""
        if not self.selected_item:
            messagebox.showwarning("No Selection", "Please select a record to edit")
            return
        
        # Switch to edit tab
        self.notebook.select(2)
        
        # Populate edit fields
        key_name = self.table_schema['keys'][0]
        self.edit_pk_name_var.set(key_name)
        self.edit_pk_value_var.set(str(self.selected_item[key_name]))
        
        # Load JSON
        self.edit_text.delete(1.0, tk.END)
        self.edit_text.insert(1.0, json.dumps(self.selected_item, indent=2, cls=DecimalEncoder))
    
    def load_record_for_edit(self):
        """Load record by key for editing"""
        if not self.current_table:
            messagebox.showwarning("No Table", "Please select a table first")
            return
        
        key_name = self.edit_pk_name_var.get()
        key_value = self.edit_pk_value_var.get()
        
        if not key_name or not key_value:
            messagebox.showwarning("Invalid Key", "Please enter key name and value")
            return
        
        try:
            table = self.dynamodb.Table(self.current_table)
            response = table.get_item(Key={key_name: key_value})
            
            if 'Item' in response:
                item = response['Item']
                self.edit_text.delete(1.0, tk.END)
                self.edit_text.insert(1.0, json.dumps(item, indent=2, cls=DecimalEncoder))
                self.status_var.set("Record loaded for editing")
            else:
                messagebox.showinfo("Not Found", "No record found with that key")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load record:\n{str(e)}")
    
    def save_record(self):
        """Save edited record"""
        if not self.current_table:
            messagebox.showwarning("No Table", "Please select a table first")
            return
        
        # Validate JSON
        try:
            json_text = self.edit_text.get(1.0, tk.END)
            item = json.loads(json_text)
        except json.JSONDecodeError as e:
            messagebox.showerror("Invalid JSON", f"JSON parsing error:\n{str(e)}")
            return
        
        if not messagebox.askyesno("Confirm Save", 
            "Are you sure you want to save these changes?"):
            return
        
        try:
            table = self.dynamodb.Table(self.current_table)
            table.put_item(Item=item)
            
            messagebox.showinfo("Success", "Record saved successfully")
            self.status_var.set("Record updated")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save record:\n{str(e)}")
    
    def cancel_edit(self):
        """Cancel editing"""
        if messagebox.askyesno("Cancel Edit", "Discard changes?"):
            self.edit_text.delete(1.0, tk.END)
            self.edit_pk_value_var.set('')
    
    def validate_json(self):
        """Validate JSON syntax"""
        try:
            json_text = self.edit_text.get(1.0, tk.END)
            json.loads(json_text)
            messagebox.showinfo("Valid JSON", "✅ JSON syntax is valid")
        except json.JSONDecodeError as e:
            messagebox.showerror("Invalid JSON", f"JSON parsing error:\n{str(e)}")
    
    def execute_query(self):
        """Execute query builder query"""
        if not self.current_table:
            messagebox.showwarning("No Table", "Please select a table first")
            return
        
        try:
            table = self.dynamodb.Table(self.current_table)
            
            pk_name = self.pk_name_var.get()
            pk_value = self.pk_value_var.get()
            
            if pk_name and pk_value:
                # Query by primary key
                response = table.query(
                    KeyConditionExpression=Key(pk_name).eq(pk_value)
                )
            else:
                # Scan with filter
                filter_attr = self.filter_attr_var.get()
                filter_value = self.filter_value_var.get()
                filter_op = self.filter_op_var.get()
                
                if filter_attr and filter_value:
                    if filter_op == '=':
                        filter_expr = Attr(filter_attr).eq(filter_value)
                    elif filter_op == '!=':
                        filter_expr = Attr(filter_attr).ne(filter_value)
                    elif filter_op == '<':
                        filter_expr = Attr(filter_attr).lt(float(filter_value))
                    elif filter_op == '<=':
                        filter_expr = Attr(filter_attr).lte(float(filter_value))
                    elif filter_op == '>':
                        filter_expr = Attr(filter_attr).gt(float(filter_value))
                    elif filter_op == '>=':
                        filter_expr = Attr(filter_attr).gte(float(filter_value))
                    elif filter_op == 'contains':
                        filter_expr = Attr(filter_attr).contains(filter_value)
                    elif filter_op == 'begins_with':
                        filter_expr = Attr(filter_attr).begins_with(filter_value)
                    
                    response = table.scan(FilterExpression=filter_expr)
                else:
                    response = table.scan()
            
            items = response.get('Items', [])
            
            # Display results
            result_text = json.dumps(items, indent=2, cls=DecimalEncoder)
            self.query_results_text.delete(1.0, tk.END)
            self.query_results_text.insert(1.0, result_text)
            
            self.status_var.set(f"Query returned {len(items)} records")
            
        except Exception as e:
            messagebox.showerror("Query Error", f"Failed to execute query:\n{str(e)}")
    
    def scan_table(self):
        """Scan entire table"""
        if not self.current_table:
            messagebox.showwarning("No Table", "Please select a table first")
            return
        
        try:
            self.status_var.set("Scanning table...")
            table = self.dynamodb.Table(self.current_table)
            
            response = table.scan()
            items = response.get('Items', [])
            
            # Handle pagination
            while 'LastEvaluatedKey' in response:
                response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
                items.extend(response.get('Items', []))
            
            result_text = json.dumps(items, indent=2, cls=DecimalEncoder)
            self.query_results_text.delete(1.0, tk.END)
            self.query_results_text.insert(1.0, result_text)
            
            self.status_var.set(f"Scanned {len(items)} records")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to scan table:\n{str(e)}")
    
    def clear_query(self):
        """Clear query fields"""
        self.pk_value_var.set('')
        self.filter_attr_var.set('')
        self.filter_value_var.set('')
        self.query_results_text.delete(1.0, tk.END)
    
    def execute_raw_query(self):
        """Execute raw query"""
        messagebox.showinfo("Not Implemented", "Raw query execution coming soon")
    
    def bulk_delete(self):
        """Bulk delete records"""
        if not self.current_table:
            messagebox.showwarning("No Table", "Please select a table first")
            return
        
        attr = self.bulk_attr_var.get()
        value = self.bulk_value_var.get()
        
        if not attr or not value:
            messagebox.showwarning("Invalid Input", "Please enter attribute and value")
            return
        
        if not messagebox.askyesno("⚠️ Confirm Bulk Delete", 
            f"This will DELETE ALL records where {attr} = {value}\n\n"
            f"This action CANNOT be undone!\n\n"
            f"Are you absolutely sure?"):
            return
        
        try:
            table = self.dynamodb.Table(self.current_table)
            
            # Scan for matching items
            response = table.scan(FilterExpression=Attr(attr).eq(value))
            items = response.get('Items', [])
            
            if not items:
                messagebox.showinfo("No Matches", "No records found matching the criteria")
                return
            
            # Confirm count
            if not messagebox.askyesno("Final Confirmation", 
                f"Found {len(items)} matching records.\n\n"
                f"Delete all of them?"):
                return
            
            # Delete each item
            deleted = 0
            for item in items:
                key = {}
                for key_name in self.table_schema['keys']:
                    key[key_name] = item[key_name]
                
                table.delete_item(Key=key)
                deleted += 1
            
            messagebox.showinfo("Success", f"Deleted {deleted} records")
            self.status_var.set(f"Bulk deleted {deleted} records")
            
        except Exception as e:
            messagebox.showerror("Error", f"Bulk delete failed:\n{str(e)}")
    
    def export_to_csv(self):
        """Export current view to CSV"""
        if not self.current_data:
            messagebox.showinfo("No Data", "Load records first")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"{self.current_table}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        
        if not filename:
            return
        
        try:
            # Get all columns
            columns = set()
            for item in self.current_data:
                columns.update(item.keys())
            columns = sorted(list(columns))
            
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=columns)
                writer.writeheader()
                
                for item in self.current_data:
                    # Convert complex types to strings
                    row = {}
                    for col in columns:
                        value = item.get(col, '')
                        if isinstance(value, (dict, list)):
                            value = json.dumps(value, cls=DecimalEncoder)
                        elif isinstance(value, Decimal):
                            value = float(value)
                        row[col] = value
                    writer.writerow(row)
            
            messagebox.showinfo("Success", f"Exported {len(self.current_data)} records to:\n{filename}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Export failed:\n{str(e)}")
    
    def export_table(self, format_type):
        """Export entire table"""
        if not self.current_table:
            messagebox.showwarning("No Table", "Please select a table first")
            return
        
        # Load all data
        try:
            self.status_var.set("Loading all records...")
            table = self.dynamodb.Table(self.current_table)
            
            response = table.scan()
            items = response.get('Items', [])
            
            while 'LastEvaluatedKey' in response:
                response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
                items.extend(response.get('Items', []))
            
            # Save to file
            if format_type == 'json':
                filename = filedialog.asksaveasfilename(
                    defaultextension=".json",
                    filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                    initialfile=f"{self.current_table}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                )
                
                if filename:
                    with open(filename, 'w') as f:
                        json.dump(items, f, indent=2, cls=DecimalEncoder)
                    messagebox.showinfo("Success", f"Exported {len(items)} records to JSON")
            
            elif format_type == 'csv':
                filename = filedialog.asksaveasfilename(
                    defaultextension=".csv",
                    filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                    initialfile=f"{self.current_table}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                )
                
                if filename:
                    columns = set()
                    for item in items:
                        columns.update(item.keys())
                    columns = sorted(list(columns))
                    
                    with open(filename, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=columns)
                        writer.writeheader()
                        
                        for item in items:
                            row = {}
                            for col in columns:
                                value = item.get(col, '')
                                if isinstance(value, (dict, list)):
                                    value = json.dumps(value, cls=DecimalEncoder)
                                elif isinstance(value, Decimal):
                                    value = float(value)
                                row[col] = value
                            writer.writerow(row)
                    
                    messagebox.showinfo("Success", f"Exported {len(items)} records to CSV")
            
            self.status_var.set(f"Exported {len(items)} records")
            
        except Exception as e:
            messagebox.showerror("Error", f"Export failed:\n{str(e)}")
    
    def refresh_table_info(self):
        """Refresh table information"""
        if not self.current_table:
            messagebox.showwarning("No Table", "Please select a table first")
            return
        
        try:
            client = boto3.client('dynamodb', region_name=self.region)
            response = client.describe_table(TableName=self.current_table)
            
            info = json.dumps(response['Table'], indent=2, cls=DecimalEncoder)
            self.table_info_text.delete(1.0, tk.END)
            self.table_info_text.insert(1.0, info)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to get table info:\n{str(e)}")

def main():
    root = tk.Tk()
    app = DynamoDBManagerGUI(root)
    root.mainloop()

if __name__ == '__main__':
    main()

