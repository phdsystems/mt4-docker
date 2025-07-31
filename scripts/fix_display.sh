#!/bin/bash

# Fix display rendering issues in Wine

export DISPLAY=:99
export WINEPREFIX=/root/.wine

# Set Wine to use native Windows rendering
wine reg add "HKEY_CURRENT_USER\Software\Wine\X11 Driver" /v "UseXRandR" /t REG_SZ /d "Y" /f
wine reg add "HKEY_CURRENT_USER\Software\Wine\X11 Driver" /v "UseXVidMode" /t REG_SZ /d "Y" /f
wine reg add "HKEY_CURRENT_USER\Software\Wine\Direct3D" /v "UseGLSL" /t REG_SZ /d "disabled" /f

# Fix DPI settings
wine reg add "HKEY_CURRENT_USER\Control Panel\Desktop" /v "LogPixels" /t REG_DWORD /d 96 /f
wine reg add "HKEY_CURRENT_USER\Software\Wine\Fonts" /v "Replacements" /t REG_SZ /d "MS Shell Dlg"="Tahoma" /f

# Set better rendering mode
wine reg add "HKEY_CURRENT_USER\Software\Wine\X11 Driver" /v "ClientSideWithRender" /t REG_SZ /d "N" /f
wine reg add "HKEY_CURRENT_USER\Software\Wine\X11 Driver" /v "ClientSideGraphics" /t REG_SZ /d "N" /f

# Fix window manager hints
wine reg add "HKEY_CURRENT_USER\Software\Wine\X11 Driver" /v "Managed" /t REG_SZ /d "Y" /f
wine reg add "HKEY_CURRENT_USER\Software\Wine\X11 Driver" /v "Decorated" /t REG_SZ /d "Y" /f

echo "Display fixes applied"