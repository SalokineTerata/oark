param([int]$ParentId)
# Empêche la mise en veille tant que le processus parent tourne.
Add-Type -Namespace Win32 -Name Power -MemberDefinition '[DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint flags);'
while (Get-Process -Id $ParentId -ErrorAction SilentlyContinue) {
    [void][Win32.Power]::SetThreadExecutionState(0x80000003)
    Start-Sleep -Seconds 30
}
