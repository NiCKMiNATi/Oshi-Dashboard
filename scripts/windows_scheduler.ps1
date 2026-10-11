# Internal JSON transport. Only the exact task name and inspected definition may change.
$ErrorActionPreference = "Stop"
[Console]::InputEncoding = New-Object System.Text.UTF8Encoding
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding
$request = [Console]::In.ReadToEnd() | ConvertFrom-Json
if ($request.name -cne "Oshi Dashboard Background Fetch") { throw "Unexpected task name" }
$userSid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$service = New-Object -ComObject "Schedule.Service"
$service.Connect()
$folder = $service.GetFolder("\")
function Get-OshiTask {
  # Enumeration distinguishes absence from access/service errors without swallowing them.
  @($folder.GetTasks(1)) | Where-Object { $_.Name -eq $request.name } | Select-Object -First 1
}
$task = Get-OshiTask
if ($request.operation -ne "status") {
  if ($task) {
    if ($task.Xml -cne $request.expected_xml) { throw "Task changed since inspection" }
    [xml]$existing = $task.Xml
    if ($existing.Task.Principals.Principal.UserId -ne $userSid -or
        -not $existing.Task.RegistrationInfo.Description.StartsWith("Oshi Dashboard background fetch v1:")) {
      throw "Unrecognized task owner"
    }
  } elseif ($request.expected_xml) { throw "Task disappeared since inspection" }
  switch ($request.operation) {
    "register" {
      # Create-only on absence avoids replacing a task created since inspection.
      # TASK_CREATE=2, TASK_UPDATE=4, TASK_LOGON_INTERACTIVE_TOKEN=3. No password/admin.
      $flags = if ($task) { 4 } else { 2 }
      $null = $folder.RegisterTask($request.name, $request.xml, $flags, $userSid, $null, 3, $null)
    }
    "enable" { if (-not $task) { throw "Task missing" }; $task.Enabled = $true }
    "disable" { if ($task) { $task.Enabled = $false } }
    "run" { if (-not $task) { throw "Task missing" }; $null = $task.Run($null) }
    default { throw "Unknown operation" }
  }
  $task = Get-OshiTask
}
function Utc-Time($value) {
  if ($value -and $value.Year -gt 1900) { $value.ToUniversalTime().ToString("o") } else { $null }
}
if ($task) {
  $states = @("Unknown", "Disabled", "Queued", "Ready", "Running")
  @{
    installed = $true; enabled = [bool]$task.Enabled; user = $userSid; xml = $task.Xml
    state = $states[[int]$task.State]; last_run = (Utc-Time $task.LastRunTime)
    next_run = (Utc-Time $task.NextRunTime); last_result = [long]$task.LastTaskResult
  } | ConvertTo-Json -Compress
} else {
  @{ installed = $false; user = $userSid } | ConvertTo-Json -Compress
}
