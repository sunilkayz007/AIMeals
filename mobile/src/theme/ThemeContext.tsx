import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { useColorScheme as useSystemColorScheme } from 'react-native';
import * as SecureStore from 'expo-secure-store';
import { lightColors, darkColors, type ThemeColors } from './colors';

export type ThemeMode = 'light' | 'dark' | 'system';

interface ThemeContextValue {
  mode: ThemeMode;
  resolvedScheme: 'light' | 'dark'; // 'system' resolved to an actual value
  colors: ThemeColors;
  setMode: (mode: ThemeMode) => void;
}

const THEME_MODE_KEY = 'aimeals_theme_mode';

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const systemScheme = useSystemColorScheme(); // 'light' | 'dark' | null
  const [mode, setModeState] = useState<ThemeMode>('system');
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    SecureStore.getItemAsync(THEME_MODE_KEY)
      .then((stored) => {
        if (stored === 'light' || stored === 'dark' || stored === 'system') {
          setModeState(stored);
        }
      })
      .finally(() => setIsLoaded(true));
  }, []);

  const setMode = (newMode: ThemeMode) => {
    setModeState(newMode);
    SecureStore.setItemAsync(THEME_MODE_KEY, newMode).catch(() => {});
  };

  const resolvedScheme: 'light' | 'dark' =
    mode === 'system' ? (systemScheme === 'dark' ? 'dark' : 'light') : mode;

  const colors = resolvedScheme === 'dark' ? darkColors : lightColors;

  const value = useMemo(
    () => ({ mode, resolvedScheme, colors, setMode }),
    [mode, resolvedScheme, colors]
  );

  // Don't render children until we've checked for a stored preference —
  // avoids a flash of the wrong theme on app start.
  if (!isLoaded) return null;

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    throw new Error('useTheme() must be used within a ThemeProvider — check app/_layout.tsx');
  }
  return ctx;
}
