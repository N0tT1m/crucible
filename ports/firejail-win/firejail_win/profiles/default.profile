# Default safe-ish baseline for Windows.
private-tmp
blacklist %USERPROFILE%\.aws
blacklist %USERPROFILE%\.ssh
blacklist %USERPROFILE%\AppData\Roaming\Microsoft\Credentials
blacklist %USERPROFILE%\AppData\Local\Microsoft\Vault
read-only %USERPROFILE%\.gitconfig
