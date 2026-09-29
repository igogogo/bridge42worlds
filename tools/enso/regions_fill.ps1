# Заполнение годов и норм новых боксов OISST (29.09): по три плашки параллельно (PSL отдаёт 502 при
# шести), сначала годы нормы 1991–2020 и аналоги, затем текущий год, нормы, лёгкий прогон целиком и
# полная выкладка. Журнал: data\enso\regions-fill-<дата>.log; по плашкам years-<плашка>-<дата>.log.
$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location "$root\tools\enso"
$env:PYTHONIOENCODING = 'utf-8'
$day = Get-Date -Format 'yyyy-MM-dd'
$log = "$root\data\enso\regions-fill-$day.log"
function Say($t) { "$(Get-Date -Format 'HH:mm:ss') $t" | Out-File $log -Append -Encoding utf8 }
function Batch($slabs) {
  $procs = @()
  foreach ($s in $slabs) {
    $procs += Start-Process -FilePath python -ArgumentList '-u','oisst_years.py',"--slab=$s",'--clim-years' -WorkingDirectory "$root\tools\enso" -WindowStyle Hidden -PassThru -RedirectStandardOutput "$root\data\enso\years-$s-$day.log" -RedirectStandardError "$root\data\enso\years-$s-$day.err"
  }
  $procs | Wait-Process
  Say "batch done: $($slabs -join ', ')"
}
Say "=== years for the new boxes"
Batch @('gulf','eaus','med')
Batch @('panama','barents','bengal')
Say "=== current year"
python -u oisst_years.py --current 2>&1 | Out-File $log -Append -Encoding utf8
Say "=== climatologies"
python -u oisst.py --clim 2>&1 | Out-File $log -Append -Encoding utf8
python -u oisst.py --check-clim 2>&1 | Out-File $log -Append -Encoding utf8
Say "=== light chain"
& powershell -NoProfile -ExecutionPolicy Bypass -File "$root\tools\enso\light_daily.ps1"
Say "=== full publish"
python -u publish.py --yes 2>&1 | Out-File $log -Append -Encoding utf8
Say "=== done"
