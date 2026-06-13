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
        # Read what Claude just finished
        event = json.load(sys.stdin)
        tool = event.get("tool", "")
        
        # If Claude just finished a significant task — notify you
        if tool in ["Bash", "Write", "Edit"]:
            notify(
                "Claude Finished",
                f"Task complete: {tool} — come check the results"
            )
    except Exception as e:
        # Never block Claude if hook fails
        pass

if __name__ == "__main__":
    main()