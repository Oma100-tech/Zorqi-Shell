import tkinter as tk
from tkinter import messagebox
import subprocess
import os

# Full phase list
PHASES = [f"phase{i}.bat" for i in range(1, 11)]

def run_all_phases():
    for phase in PHASES:
        phase_path = os.path.join("phases", phase)
        if os.path.exists(phase_path):
            log_text.insert(tk.END, f"▶ Running {phase}...\n")
            log_text.see(tk.END)
            root.update()
            subprocess.run(['cmd.exe', '/c', phase_path], creationflags=subprocess.CREATE_NO_WINDOW)
            log_text.insert(tk.END, f"✓ {phase} completed.\n\n")
        else:
            log_text.insert(tk.END, f"❌ {phase} not found!\n")
            log_text.see(tk.END)
            messagebox.showerror("Missing Phase", f"{phase} is missing.")
            return
    messagebox.showinfo("Success", "All phases completed. Powershell 30 is ready!")

# Setup GUI
root = tk.Tk()
root.title("Powershell 30 Installer")
root.geometry("520x350")
root.configure(bg="#1e1e1e")

label = tk.Label(root, text="Powershell 30 Full Installer", font=("Segoe UI", 14), fg="#00FF88", bg="#1e1e1e")
label.pack(pady=10)

install_btn = tk.Button(root, text="Start Installation", font=("Segoe UI", 11), bg="#2e2e2e", fg="white", command=run_all_phases)
install_btn.pack(pady=10)

log_text = tk.Text(root, height=14, width=62, bg="#121212", fg="#00ff88", font=("Consolas", 10))
log_text.pack(pady=10)
log_text.insert(tk.END, "Installer ready. Click 'Start Installation' to begin.\n")

footer = tk.Label(root, text="by Omar / OptiFlex", font=("Segoe UI", 9), fg="gray", bg="#1e1e1e")
footer.pack(pady=4)

root.mainloop()
