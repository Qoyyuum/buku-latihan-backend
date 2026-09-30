import { useSyncExternalStore } from 'react';
import { useColorScheme as useRNColorScheme } from 'react-native';

/**
 * To support static rendering, this value needs to be re-calculated on the
 * client side for web. `useSyncExternalStore` reports `false` during the
 * server snapshot so there is no hydration mismatch.
 */
export function useColorScheme() {
  const hydrated = useSyncExternalStore(
    () => () => {},
    () => true,
    () => false,
  );
  const colorScheme = useRNColorScheme();
  return hydrated ? colorScheme : 'light';
}
