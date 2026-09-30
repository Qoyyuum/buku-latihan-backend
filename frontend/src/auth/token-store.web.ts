import AsyncStorage from '@react-native-async-storage/async-storage';

const ACCESS_KEY = 'bl_access_token';
const REFRESH_KEY = 'bl_refresh_token';

export const tokenStore = {
  async save(access: string, refresh: string): Promise<void> {
    await AsyncStorage.setItem(ACCESS_KEY, access);
    await AsyncStorage.setItem(REFRESH_KEY, refresh);
  },
  async access(): Promise<string | null> {
    return AsyncStorage.getItem(ACCESS_KEY);
  },
  async refresh(): Promise<string | null> {
    return AsyncStorage.getItem(REFRESH_KEY);
  },
  async clear(): Promise<void> {
    await AsyncStorage.multiRemove([ACCESS_KEY, REFRESH_KEY]);
  },
};
