import json
import sys
import subprocess

def notify(title, message):
    """Send a Windows notification"""
    subprocess.run([
        "powershell", "-Command",
        f"""
        Add-Type -AssemblyName System.Windows.Forms
        $notify = New-Object System.Windows.Forms.NotifyIcon
        $notify.Icon = [System.Drawing.SystemIcons]::Information
        $notify.Visible = $true
        $notify.ShowBalloonTip(5000, '{title}', '{message}', 
        [System.Windows.Forms.ToolTipIcon]::Info)
        """
    ])

def main():
    try:
        # Read what Claude is about to do
        event = json.load(sys.stdin)
        tool = event.get("tool", "")
        
        # If Claude is asking for input — notify you
        if tool in ["ask", "input", "confirm"]:
            notify(
                "Claude Needs You",
                "Claude is waiting for your input"
            )
    except Exception as e:
        # Never block Claude if hook fails
        pass

if __name__ == "__main__":
    main()