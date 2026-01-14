import pandas as pd
import matplotlib.pyplot as plt
from tkinter import *
from tkinter import ttk, filedialog, messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import os

# Global DataFrame
df = pd.DataFrame()


def load_data():
    global df
    file_path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
    if not file_path:
        return
    try:
        df = pd.read_csv(file_path, parse_dates=['BorrowDate'])
        if 'Count' not in df.columns or 'BorrowDate' not in df.columns:
            messagebox.showerror("Error", "Required columns 'Count' and 'BorrowDate' not found in the CSV.")
            df = pd.DataFrame()
            return

        messagebox.showinfo("Success", f"Loaded: {os.path.basename(file_path)}")
        update_filters()
        plot_selected()
    except Exception as e:
        messagebox.showerror("Error", f"Cannot read file or missing required data: {e}")


def update_filters():
    """Populate genre & year filters based on loaded data."""
    if df.empty:
        genre_box['values'] = ['All']
        year_box['values'] = ['All']
        return

    genres = ['All']
    if 'Genre' in df.columns:
        genres = ['All'] + sorted(df['Genre'].dropna().unique().tolist())
    
    year_values = ['All']
    if 'BorrowDate' in df.columns:
        valid_years = df['BorrowDate'].dt.year.dropna().astype(int).unique().astype(str).tolist()
        year_values = ['All'] + sorted(valid_years)
        
    genre_box['values'] = genres
    year_box['values'] = year_values
    
    genre_box.current(0)
    year_box.current(0)


def apply_filters():
    if df.empty:
        return pd.DataFrame()
        
    filtered = df.copy()
    genre = genre_box.get()
    year = year_box.get()

    if genre != 'All' and 'Genre' in filtered.columns:
        filtered = filtered[filtered['Genre'] == genre]

    if year != 'All' and 'BorrowDate' in filtered.columns:
        try:
            filtered = filtered[filtered['BorrowDate'].dt.year == int(year)]
        except ValueError:
            pass 
            
    return filtered


def plot_selected():
    filtered = apply_filters()
    
    
    for canvas in [bar_canvas, pie_canvas, line_canvas]:
        canvas.get_tk_widget().grid_forget()
    
    line_chart_frame.pack_forget() # Hide the line chart container frame

    if filtered.empty:
        messagebox.showwarning("No Data", "No records for selected filters!")
        return

    row, col = 0, 0
    
    # Bar Chart 
    if bar_var.get():
        plot_bar(filtered)
        bar_canvas.get_tk_widget().grid(row=row, column=col, padx=20, pady=10, sticky="nsew")
        col += 1
        
    # Pie Chart 
    if pie_var.get():
        plot_pie(filtered)
        pie_canvas.get_tk_widget().grid(row=row, column=col, padx=20, pady=10, sticky="nsew")
        col += 1
        
    # Line Chart 
    if line_var.get():
        plot_line(filtered)
        line_chart_frame.pack(fill=X, pady=(0, 20))


def plot_bar(filtered):
    ax1.clear()
    if 'Title' in filtered.columns and 'Count' in filtered.columns:
        data = filtered.groupby('Title')['Count'].sum().sort_values(ascending=False).head(5)
        bars = ax1.bar(data.index, data.values, color=['#007ACC', '#4CAF50', '#FF9800', '#F44336', '#9C27B0'])
        ax1.set_title("📚 Top 5 Most Borrowed Books", fontsize=12, fontweight='bold', color="#333333")
        ax1.set_ylabel("Borrow Count", fontsize=10)
        ax1.tick_params(axis='x', rotation=30, labelsize=8)
        ax1.bar_label(bars, fmt='%d', fontsize=8)
    else:
        ax1.set_title("Missing 'Title' or 'Count' column for Bar Chart")
    fig1.tight_layout()
    bar_canvas.draw()


def plot_pie(filtered):
    """Draws the Department-wise Borrowing pie chart."""
    ax2.clear()
    if 'Department' in filtered.columns and 'Count' in filtered.columns:
        data = filtered.groupby('Department')['Count'].sum()
        if data.sum() > 0:
            colors = plt.cm.Pastel1.colors[:len(data)]
            ax2.pie(data, labels=data.index, autopct='%1.1f%%', startangle=90, colors=colors, textprops={'fontsize': 9})
            ax2.set_title("🏫 Department-wise Borrowing", fontsize=12, fontweight='bold', color="#333333")
            ax2.axis('equal')
        else:
            ax2.set_title("No Borrow Count data for Pie Chart")
    else:
        ax2.set_title("Missing 'Department' or 'Count' column for Pie Chart")
    fig2.tight_layout()
    pie_canvas.draw()


def plot_line(filtered):
    """Draws the Monthly Borrowing Trend line chart."""
    ax3.clear()
    if 'BorrowDate' in filtered.columns and 'Count' in filtered.columns:
        data = filtered.copy()
        data['Month'] = data['BorrowDate'].dt.to_period('M')
        trend = data.groupby('Month')['Count'].sum()
        
        if not trend.empty:
            ax3.plot(trend.index.astype(str), trend.values, marker='o', linestyle='-', color="#FF6347", linewidth=2.5)
            ax3.set_title("📈 Monthly Borrowing Trend", fontsize=12, fontweight='bold', color="#333333")
            ax3.set_ylabel("Borrow Count")
            ax3.set_xlabel("Month")
            ax3.tick_params(axis='x', rotation=45, labelsize=9)
            ax3.grid(True, linestyle='--', alpha=0.6)
        else:
            ax3.set_title("No data for Monthly Borrowing Trend")
    else:
        ax3.set_title("Missing 'BorrowDate' or 'Count' column for Line Chart")
    fig3.tight_layout()
    line_canvas.draw()


def export_charts():
    folder = filedialog.askdirectory()
    if not folder:
        return
     
    exported_count = 0
    if bar_var.get():
        bar_canvas.figure.savefig(os.path.join(folder, "bar_chart.png"), dpi=300)
        exported_count += 1
    if pie_var.get():
        pie_canvas.figure.savefig(os.path.join(folder, "pie_chart.png"), dpi=300)
        exported_count += 1
    if line_var.get():
        line_canvas.figure.savefig(os.path.join(folder, "line_chart.png"), dpi=300)
        exported_count += 1
        
    if exported_count > 0:
        messagebox.showinfo("Exported", f"{exported_count} chart(s) saved to: {folder}")
    else:
        messagebox.showwarning("No Selection", "Please select at least one chart to export.")


def show_dataset():
    if df.empty:
        messagebox.showwarning("No Data", "Please load a CSV file first.")
        return

    data_window = Toplevel(root)
    data_window.title(" Raw Dataset View")
    
    data_frame = Frame(data_window)
    data_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)

    tree = ttk.Treeview(data_frame)
    tree.pack(side=LEFT, fill=BOTH, expand=True)

    vsb = ttk.Scrollbar(data_frame, orient="vertical", command=tree.yview)
    vsb.pack(side=RIGHT, fill=Y)
    hsb = ttk.Scrollbar(data_frame, orient="horizontal", command=tree.xview)
    hsb.pack(side=BOTTOM, fill=X)
    
    tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

    columns = list(df.columns)
    tree["columns"] = columns
    tree["show"] = "headings"

    for col in columns:
        tree.heading(col, text=col.replace('_', ' ').title(), anchor=W)
        tree.column(col, width=100, anchor=W)

    for _, row in df.iterrows():
        display_row = [str(val) if pd.notna(val) else '' for val in row.values]
        tree.insert("", "end", values=display_row)
        
    for col in columns:
        col_width = max(tree.heading(col, option="text").replace('_', ' ').title().__len__() * 10, 100)
        data_widths = [len(str(df[col].iloc[i])) * 8 for i in range(min(100, len(df)))]
        if data_widths:
            col_width = max(col_width, max(data_widths))
        tree.column(col, width=min(col_width, 300))
        
    data_window.update_idletasks()
    window_width = data_window.winfo_reqwidth()
    window_height = data_window.winfo_reqheight()
    position_right = int(data_window.winfo_screenwidth() / 2 - window_width / 2)
    position_down = int(data_window.winfo_screenheight() / 2 - window_height / 2)
    data_window.geometry(f"+{position_right}+{position_down}")


root = Tk()
root.title("Librarian Data Insights Dashboard")
root.minsize(1200, 750) 
root.config(bg="#F0F2F5")

# Custom Styling
style = ttk.Style()
style.theme_use('clam')
style.configure("TButton", font=("Segoe UI", 11, "bold"), padding=8, background="#007ACC", foreground="white", borderwidth=0)
style.map("TButton", background=[('active', '#005FA3')])
style.configure("TLabel", font=("Segoe UI", 10))
style.configure("TCombobox", font=("Segoe UI", 10), padding=5)


# Helper function for flat-style buttons with hover effect
def make_flat_button(parent, text, color, cmd):
    b = Button(parent, text=text, bg=color, fg="white", font=("Segoe UI", 10, "bold"), 
               padx=15, pady=5, activebackground=color, borderwidth=0, command=cmd)
    hover_color = '#005FA3' if color == '#007ACC' else color
    b.bind("<Enter>", lambda e: b.config(bg=hover_color))
    b.bind("<Leave>", lambda e: b.config(bg=color))
    return b


# --- 1. Header (Top Bar) ---

header = Frame(root, bg="#007ACC")
header.pack(fill=X)
Label(header, text=" Librarian Data Insights Dashboard", bg="#007ACC", fg="white",
      font=("Segoe UI", 16, "bold"), pady=10).pack(pady=5)

control_frame = Frame(root, bg="#FFFFFF", padx=10, pady=10, relief=FLAT)
control_frame.pack(fill=X, padx=10, pady=(10, 5))


control_frame.columnconfigure((0, 5, 6, 7), weight=1)
control_frame.columnconfigure((1, 2, 3, 4), weight=0)

make_flat_button(control_frame, " Load CSV", "#09431D", load_data).grid(row=0, column=0, padx=15, sticky='w')

Label(control_frame, text="Filter by Genre:", bg="#FFFFFF", font=("Segoe UI", 10, 'bold')).grid(row=0, column=1, padx=(30, 5), sticky='w')
genre_box = ttk.Combobox(control_frame, state='readonly', width=18)
genre_box.grid(row=0, column=2, padx=5, sticky='w')
genre_box['values'] = ['All']

Label(control_frame, text="Filter by Year:", bg="#FFFFFF", font=("Segoe UI", 10, 'bold')).grid(row=0, column=3, padx=(15, 5), sticky='w')
year_box = ttk.Combobox(control_frame, state='readonly', width=10)
year_box.grid(row=0, column=4, padx=5, sticky='w')
year_box['values'] = ['All']

make_flat_button(control_frame, " Apply Filters","#28A745", lambda: plot_selected()).grid(row=0, column=5, padx=15)
make_flat_button(control_frame, " View Data", "#FF8C00", show_dataset).grid(row=0, column=6, padx=15)
make_flat_button(control_frame, " Export Charts", "#FF6347", export_charts).grid(row=0, column=7, padx=15, sticky='e')


# --- 3. Chart Selection Frame ---
selection_frame = Frame(root, bg="#E8EEF9", relief=FLAT, bd=0)
selection_frame.pack(pady=5, fill=X, padx=10)
Label(selection_frame, text="Select Charts to Display:", bg="#E8EEF9", font=("Segoe UI", 10, "bold")).pack(side=LEFT, padx=15, pady=5)

bar_var = BooleanVar(value=True)
pie_var = BooleanVar(value=True)
line_var = BooleanVar(value=True)

Checkbutton(selection_frame, text="Top Books Bar Chart", variable=bar_var, bg="#E8EEF9", font=("Segoe UI", 9), command=plot_selected).pack(side=LEFT, padx=10)
Checkbutton(selection_frame, text="Department Pie Chart", variable=pie_var, bg="#E8EEF9", font=("Segoe UI", 9), command=plot_selected).pack(side=LEFT, padx=10)
Checkbutton(selection_frame, text="Monthly Trend Line Chart", variable=line_var, bg="#E8EEF9", font=("Segoe UI", 9), command=plot_selected).pack(side=LEFT, padx=10)



chart_container = Frame(root, bg="#F0F2F5")
chart_container.pack(fill=BOTH, expand=True, padx=10)


top_chart_frame = Frame(chart_container, bg="#F0F2F5")
top_chart_frame.pack(fill=X, pady=(10, 0))
top_chart_frame.columnconfigure((0, 1), weight=1)


line_chart_frame = Frame(chart_container, bg="#FFFFFF", relief=FLAT, bd=1)


fig1, ax1 = plt.subplots(figsize=(6, 4), facecolor='#FFFFFF')
bar_canvas = FigureCanvasTkAgg(fig1, master=top_chart_frame)

fig2, ax2 = plt.subplots(figsize=(6, 4), facecolor='#FFFFFF')
pie_canvas = FigureCanvasTkAgg(fig2, master=top_chart_frame)

fig3, ax3 = plt.subplots(figsize=(12, 4), facecolor='#FFFFFF')
line_canvas = FigureCanvasTkAgg(fig3, master=line_chart_frame)
line_canvas.get_tk_widget().pack(fill=BOTH, expand=True, padx=15, pady=15)



footer = Frame(root, bg="#007ACC", height=30)
footer.pack(fill=X, side=BOTTOM)
Label(footer, text="© 2025 Library Data Insights | Developed with Python & Tkinter",
      bg="#007ACC", fg="white", font=("Segoe UI", 9)).pack(pady=5)


# Initial execution to clear charts on startup
plot_selected() 

root.mainloop()