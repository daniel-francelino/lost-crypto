export const NOTE_MAX_LENGTH = 2000;

export const remainingCharacters = (text: string): number => NOTE_MAX_LENGTH - text.length;

export const canSubmitNote = (text: string): boolean =>
  text.trim().length > 0 && text.length <= NOTE_MAX_LENGTH;
