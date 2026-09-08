# Ежедневный лёгкий прогон панели El Niño (владелец 06.09: «раз в день запустились, проверили,
# есть ли что новое в источниках, долили свежее, ещё не разобранное»).
#
# Что делает: лёгкий прогон (правила без модели → fresh.json, ops.json, runs.json), раздел
# истории измерений (planet.py, медленные ряды), при триггере уровня high — полный прогон с
# моделью (БЕЗ выкладки: вердикт должен пройти проверку), затем выкладка только служебного слоя
# (publish.py --fresh). Разобранное состояние на сайте не меняется без человека.
#
# Планировщик: schtasks /Create /TN b42_enso_light /SC DAILY /ST 08:30 /F
#   /TR "powershell -NoProfile -ExecutionPolicy Bypass -File C:\...\tools\enso\light_daily.ps1"
# Лог: data\enso\light-<дата>.log
$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location "$root\tools\enso"
$env:PYTHONIOENCODING = 'utf-8'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$py = 'C:\Python313\python.exe'
if (-not (Test-Path $py)) { $py = 'python' }
$day = Get-Date -Format 'yyyy-MM-dd'
$log = "$root\data\enso\light-$day.log"
function Say($t) { "$(Get-Date -Format 'HH:mm:ss') $t" | Out-File $log -Append -Encoding utf8 }

Say "=== light run"
& $py -u refresh.py --light 2>&1 | Out-File $log -Append -Encoding utf8
if ($LASTEXITCODE -ne 0) { Say "light run failed, code $LASTEXITCODE"; exit 1 }

Say "=== long record (planet.py)"
& $py -u planet.py 2>&1 | Out-File $log -Append -Encoding utf8

Say "=== mentions feed (mentions.py)"
& $py -u mentions.py 2>&1 | Out-File $log -Append -Encoding utf8

Say "=== spectral watch (spectral.py)"
& $py -u spectral.py 2>&1 | Out-File $log -Append -Encoding utf8

Say "=== land points on Dynamics (regions_daily.py)"
& $py -u regions_daily.py 2>&1 | Out-File $log -Append -Encoding utf8

Say "=== rain (precip.py)"
& $py -u precip.py 2>&1 | Out-File $log -Append -Encoding utf8

# СПУТНИК, СЫРЫЕ ГРАНУЛЫ: внешний сборщик C:\CL\radiance пишет radiance.json сам (владелец 07.09:
# «они сами будут обновлять, мы просто берём результат»). Берём копию, если файл полный:
# в нём есть детекторы и ряды за несколько лет; частичный (в середине их пересборки) не берём.
Say "=== radiance.json from the external collector"
& $py -u radiance_take.py 2>&1 | Out-File $log -Append -Encoding utf8

Say "=== globe data (globe_data.py)"
& $py -u globe_data.py 2>&1 | Out-File $log -Append -Encoding utf8

$fresh = $null
try { $fresh = Get-Content "$root\data\enso\fresh.json" -Raw -Encoding utf8 | ConvertFrom-Json } catch { Say "fresh.json unreadable: $_" }
if ($fresh -and $fresh.needs_assessment) {
  # Полный прогон с моделью — только по решению владельца в диалоге (правило 07.09): здесь лишь запись
  Say "=== TRIGGER CROSSED, full assessment is due, decide in dialogue, not started here: $($fresh.summary)"
}

Say "=== publish the fresh layer"
& $py -u publish.py --fresh --yes 2>&1 | Out-File $log -Append -Encoding utf8
if ($LASTEXITCODE -ne 0) { Say "publish --fresh failed, code $LASTEXITCODE" }
Say "=== done"
