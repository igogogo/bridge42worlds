# Укажите ваш API ключ DeepSeek здесь (или оставьте пустым, скрипт спросит его при запуске)
$DEEPSEEK_KEY = ""

# Проверяем текущее состояние по наличию переменной
if (Test-Path Env:\ANTHROPIC_BASE_URL) {
    Write-Host "--- Отключаем DeepSeek. Возвращаем оригинальный Claude... ---" -ForegroundColor Yellow
    
    # Удаляем переменные из текущей сессии
    $vars = @("ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_MODEL", 
              "ANTHROPIC_DEFAULT_OPUS_MODEL", "ANTHROPIC_DEFAULT_SONNET_MODEL", 
              "ANTHROPIC_DEFAULT_HAIKU_MODEL", "CLAUDE_CODE_SUBAGENT_MODEL", "CLAUDE_CODE_EFFORT_LEVEL")
    
    foreach ($var in $vars) {
        Remove-Item "Env:\$var" -ErrorAction SilentlyContinue
        [Environment]::SetEnvironmentVariable($var, $null, "User")
    }
    
    Write-Host "[УСПЕХ] Переменные удалены. Claude снова работает по умолчанию!" -ForegroundColor Green
    Write-Host "[ВАЖНО] Перезапустите приложение Claude или ваш терминал, чтобы изменения вступили в силу." -ForegroundColor Cyan
} 
else {
    Write-Host "--- Включаем DeepSeek для Claude... ---" -ForegroundColor Yellow
    
    # Если ключ не задан в скрипте, запрашиваем его у пользователя
    if ([string]::IsNullOrEmpty($DEEPSEEK_KEY)) {
        $DEEPSEEK_KEY = Read-Host "Вставьте ваш DeepSeek API Key"
    }
    
    if ([string]::IsNullOrEmpty($DEEPSEEK_KEY)) {
        Write-Error "API ключ не может быть пустым. Отмена операции."
        return
    }

    # Настройки для DeepSeek
    $config = @{
        "ANTHROPIC_BASE_URL"             = "https://deepseek.com"
        "ANTHROPIC_AUTH_TOKEN"           = $DEEPSEEK_KEY
        "ANTHROPIC_MODEL"                = "deepseek-v4-pro[1m]"
        "ANTHROPIC_DEFAULT_OPUS_MODEL"   = "deepseek-v4-pro[1m]"
        "ANTHROPIC_DEFAULT_SONNET_MODEL" = "deepseek-v4-pro[1m]"
        "ANTHROPIC_DEFAULT_HAIKU_MODEL"  = "deepseek-v4-flash"
        "CLAUDE_CODE_SUBAGENT_MODEL"     = "deepseek-v4-flash"
        "CLAUDE_CODE_EFFORT_LEVEL"       = "max"
    }

    # Записываем переменные в текущую сессию и сохраняем в систему (в профиль пользователя)
    foreach ($key in $config.Keys) {
        $value = $config[$key]
        Set-Content "Env:\$key" $value
        [Environment]::SetEnvironmentVariable($key, $value, "User")
    }

    Write-Host "[УСПЕХ] Настройки DeepSeek успешно применены!" -ForegroundColor Green
    Write-Host "[ВАЖНО] Обязательно перезапустите приложение Claude или терминал, чтобы они увидели новые настройки." -ForegroundColor Cyan
}
