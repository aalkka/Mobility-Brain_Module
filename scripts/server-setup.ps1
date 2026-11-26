# 외부뇌 서버 등록 — 바깥 설정 «하기»(mobility.task · mobility.serve)가 부르거나 사람이 친다(지속 설정 · 관리자 불필요).
#   powershell -NoProfile -ExecutionPolicy Bypass -File .claude\skills\mobility\scripts\server-setup.ps1            # -Task + -Serve
#   ... server-setup.ps1 -Task       # 예약 «외부뇌 서버»만(15분마다 살아 있나 보고 없으면 이 볼트 서버를 띄움)
#   ... server-setup.ps1 -Serve      # tailscale serve / → 127.0.0.1:<문 번호>만
#   ... server-setup.ps1 -Remove     # 지우기 — 이 볼트가 맡은 것만(다른 볼트의 예약·serve 는 그대로)
#   ... server-setup.ps1 -ShowKey    # 끝에 열쇠를 보인다(기본은 안 보임 — 대화·기록에 남지 않게)
# 문 번호 = conf.py 한 곳(config «port» → 조리법 기본값). 다른 볼트가 이미 맡은 예약·serve 는 덮지 않고 멈춘다(종료 1).
# 전제: Tailscale 설치·로그인(바깥 설정 mobility.tailscale·tailscale-login) · 127.0.0.1 에만 열고 밖은 tailnet 안의 기기만(Funnel 아님).
param([switch]$Remove, [switch]$Task, [switch]$Serve, [switch]$ShowKey)
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$name = '외부뇌 서버'
$sys = $PSScriptRoot                                          # mobility 모듈 scripts(server.py 가 옆에 있다)
$vault = (Resolve-Path (Join-Path $sys '..\..\..\..')).Path    # 볼트 뿌리 — 서버가 도는 자리
$server = Join-Path $sys 'server.py'
$ts = (Get-Command tailscale -ErrorAction SilentlyContinue).Source
if (-not $ts) { $ts = Join-Path $env:ProgramFiles 'Tailscale\tailscale.exe' }
$port = [int](py -3 (Join-Path $sys 'conf.py') port --vault $vault)
if (-not ($Task -or $Serve -or $Remove)) { $Task = $true; $Serve = $true }

function TaskOwner {
    # 예약이 띄우는 server.py 자리 · 없으면 $null
    $t = Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
    if (-not $t) { return $null }
    $arg = ($t.Actions | Select-Object -First 1).Arguments
    if ($arg -match '"([^"]+server\.py)"') { return $Matches[1] }
    return $arg
}
function ServeOwner {
    # serve / 가 넘기는 문 번호 · 없으면 $null · 못 읽으면 -1
    if (-not (Test-Path $ts)) { return -1 }
    try { $j = (& $ts serve status --json) | ConvertFrom-Json } catch { return -1 }
    foreach ($h in $j.Web.PSObject.Properties) {
        $p = $h.Value.Handlers.'/'.Proxy
        if ($p -match '^https?://(127\.0\.0\.1|localhost):(\d+)/?$') { return [int]$Matches[2] }
    }
    return $null
}
$mine = { param($p) $p -and ([IO.Path]::GetFullPath($p) -ieq [IO.Path]::GetFullPath($server)) }

if ($Remove) {
    $own = TaskOwner
    if (& $mine $own) {
        Stop-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
        Unregister-ScheduledTask -TaskName $name -Confirm:$false -ErrorAction SilentlyContinue
        Write-Output '예약 지움'
    } elseif ($own) { Write-Output "예약은 다른 볼트($own) 것이라 그대로 둠" }
    $sv = ServeOwner
    if ($sv -eq $port) {
        $tcp = @(((& $ts serve status --json) | ConvertFrom-Json).TCP.PSObject.Properties).Count
        if ($tcp -le 1) { & $ts serve reset | Out-Null; Write-Output 'serve 닫음' }
        else { Write-Output 'serve 에 다른 문도 있어 그대로 둠 — tailscale serve status 를 보고 손으로 닫는다'; exit 1 }
    } elseif ($sv -gt 0) { Write-Output "serve 는 다른 문($sv) 것이라 그대로 둠" }
    exit 0
}

$code = 0
if ($Task) {
    $own = TaskOwner
    if ($own -and -not (& $mine $own) -and (Test-Path $own)) {
        Write-Output "⚠ 예약 «$name» 을 다른 볼트가 맡음($own) — 덮지 않음(그 볼트에서 -Remove 뒤 다시)"
        $code = 1
    } else {
        $pyw = (Get-Command pyw -ErrorAction SilentlyContinue).Source
        if (-not $pyw) { Write-Output '⚠ pyw(파이썬 런처)를 못 찾음 — 중단'; exit 1 }
        $s = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -ExecutionTimeLimit ([TimeSpan]::Zero)
        $a = New-ScheduledTaskAction -Execute $pyw -Argument "-3 `"$server`"" -WorkingDirectory $vault
        $t = New-ScheduledTaskTrigger -Once -At (Get-Date).AddSeconds(5) -RepetitionInterval (New-TimeSpan -Minutes 15)
        # 로그온 때(ARSO 든 손 로그인이든) 바로 사용자 세션 서버 — 로그인 전 서버(세션 0 · S4U)가 있으면 server.py 가 시작할 때 넘겨받음(server_swap.take_over · 이 사용자 한정 로그온 트리거는 관리자 불필요 · 11-13 잼)
        $t2 = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
        # 실패를 «등록»으로 찍지 않는다(11-27 · 관리자 창에서 만든 예약은 사용자가 덮지 못해 0x80070005 인데 «예약 등록»이 나왔다)
        $reg = $true
        try {
            Register-ScheduledTask -TaskName $name -Action $a -Trigger @($t, $t2) -Settings $s -Force -Description '외부뇌: 폰이 PC 볼트에 닿는 문(제공·검색·폰 기록). 127.0.0.1 만 · 밖은 Tailscale.' -ErrorAction Stop | Out-Null
        } catch {
            $reg = $false
            $code = 1
            if ("$($_.FullyQualifiedErrorId) $($_.Exception.Message)" -match '0x80070005|denied|거부') {
                Write-Output "⚠ 예약 «$name» 을 못 고침 — 관리자 창에서 만든 예약이라 이 사용자는 읽기만 됨. 관리자 PowerShell 에서 한 번: Unregister-ScheduledTask -TaskName '$name' -Confirm:`$false — 그 뒤 이 대본(-Task)을 보통 창에서 다시"
            } else {
                Write-Output "⚠ 예약 등록 실패 — $($_.Exception.Message)"
            }
        }
        Start-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue      # 못 고쳤어도 옛 예약으로 서버는 띄운다(이 볼트 서버인 것은 위에서 잼)
        if ($reg) { Write-Output "예약 등록 · 서버 127.0.0.1:$port" }
    }
}
if ($Serve) {
    $sv = ServeOwner
    if (-not (Test-Path $ts)) { Write-Output '⚠ Tailscale 이 없음 — 바깥 설정 «Tailscale 설치» 뒤 다시'; exit 1 }
    elseif ($sv -eq $port) { Write-Output "serve 이미 됨(/ → 127.0.0.1:$port)"; $served = $true }
    elseif ($sv -gt 0) { Write-Output "⚠ serve / 를 다른 문($sv)이 맡음 — 덮지 않음(다른 볼트 서버면 그 볼트에서 -Remove 뒤 다시)"; $code = 1 }
    else { & $ts serve --bg $port | Out-Null; Write-Output "serve 켬(/ → 127.0.0.1:$port)"; $served = $true }
    if ($served) {
        $dns = ((& $ts status --json) | ConvertFrom-Json).Self.DNSName.TrimEnd('.')
        if ($dns) { Write-Output "주소  https://$dns · 시험 = 폰 브라우저에서 /v1/ping — «열쇠가 틀림» 이 보이면 길이 뚫린 것" }
    }
}
if ($ShowKey) { Start-Sleep -Seconds 3; Write-Output ("열쇠  " + (py -3 $server token)) }
else { Write-Output '열쇠는 안 보임(대화·기록에 안 남게) — 폰에 넣을 때만 -ShowKey' }
exit $code
