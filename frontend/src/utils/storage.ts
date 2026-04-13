import { Preferences } from '@capacitor/preferences';

const TOKEN_KEYS = {
  access: 'finanzas_access_token',
  refresh: 'finanzas_refresh_token',
} as const;

type TokenType = keyof typeof TOKEN_KEYS;

export async function getToken(type: TokenType): Promise<string | null> {
  const { value } = await Preferences.get({ key: TOKEN_KEYS[type] });
  return value;
}

export async function setTokens(access: string, refresh: string): Promise<void> {
  await Preferences.set({ key: TOKEN_KEYS.access, value: access });
  await Preferences.set({ key: TOKEN_KEYS.refresh, value: refresh });
}

export async function clearTokens(): Promise<void> {
  await Preferences.remove({ key: TOKEN_KEYS.access });
  await Preferences.remove({ key: TOKEN_KEYS.refresh });
}

export async function isAuthenticated(): Promise<boolean> {
  const token = await getToken('access');
  return token !== null;
}
