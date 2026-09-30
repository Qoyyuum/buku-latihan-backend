import AsyncStorage from '@react-native-async-storage/async-storage';
import { Directory, File, Paths } from 'expo-file-system';

import { api } from '@/api/client';
import type { WorksheetBundle } from '@/api/types';

const MANIFEST_PREFIX = 'bl_bundle_';

function worksheetDir(id: number): Directory {
  return new Directory(Paths.document, `worksheets/${id}`);
}

/**
 * Download every page image of a worksheet for offline writing.
 * Returns the bundle manifest (also cached in AsyncStorage).
 */
export async function downloadBundle(worksheetId: number): Promise<WorksheetBundle> {
  const bundle = await api.worksheetBundle(worksheetId);
  const dir = worksheetDir(worksheetId);
  dir.create({ intermediates: true, idempotent: true });

  await Promise.all(
    bundle.page_downloads.map(async (p) => {
      const file = new File(dir, `page_${p.order}.png`);
      if (!file.exists) {
        const downloaded = await File.downloadFileAsync(p.url, file);
        if (!downloaded.exists) {
          throw new Error(`Failed to download page ${p.order}`);
        }
      }
    }),
  );

  await AsyncStorage.setItem(
    `${MANIFEST_PREFIX}${worksheetId}`,
    JSON.stringify(bundle),
  );
  return bundle;
}

export async function bundleIsDownloaded(worksheetId: number): Promise<boolean> {
  const manifest = await AsyncStorage.getItem(`${MANIFEST_PREFIX}${worksheetId}`);
  if (!manifest) return false;
  const bundle = JSON.parse(manifest) as WorksheetBundle;
  return bundle.page_downloads.every((p) =>
    new File(worksheetDir(worksheetId), `page_${p.order}.png`).exists,
  );
}

/** Local file URI for a downloaded page, or null when not cached. */
export function localPageUri(worksheetId: number, order: number): string | null {
  const file = new File(worksheetDir(worksheetId), `page_${order}.png`);
  return file.exists ? file.uri : null;
}
