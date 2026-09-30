import * as SecureStore from 'expo-secure-store';

const ACCESS_KEY = 'bl_access_token';
const REFRESH_KEY = 'bl_refresh_token';

export const tokenStore = {
  async save(access: string, refresh: string): Promise<void> {
    await SecureStore.setItemAsync(ACCESS_KEY, access);
    await SecureStore.setItemAsync(REFRESH_KEY, refresh);
  },
  async access(): Promise<string | null> {
    return SecureStore.getItemAsync(ACCESS_KEY);
  },
  async refresh(): Promise<string | null> {
    return SecureStore.getItemAsync(REFRESH_KEY);
  },
  async clear(): Promise<void> {
    await SecureStore.deleteItemAsync(ACCESS_KEY);
    await SecureStore.deleteItemAsync(REFRESH_KEY);
  },
};
