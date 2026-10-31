# Editor

`@danielsoaresf/lost-ui/editor` has `RichTextEditor`, a Notion-style block editor on Tiptap 3: `/` menu for blocks, a toolbar over the selected text, a grip beside each block to drag it and open its menu, tables, to-do lists, callouts, toggles, images. It reads and writes **HTML** (default) or the Tiptap **JSON** (`format="json"`). Props: [api/editor](api/editor.md).

```tsx
import { RichTextEditor } from "@danielsoaresf/lost-ui/editor";

<RichTextEditor
  value={html}
  onValueChange={setHtml}
  placeholder="Write something, or press “/” for blocks…"
  minHeight="12rem"
  onUploadImage={async (file) => (await upload(file)).url}
/>;
```

## Rules

- It needs the Tiptap peers installed in the app (list in the library's `docs/editor.md`); an app that does not use it installs none.
- Controlled: `value` + `onValueChange` (HTML). Uncontrolled: `defaultValue`. Changing `value` from outside replaces the content without calling `onValueChange`.
- The image block shows only when `onUploadImage` is given; it must return the URL of the uploaded file. `onUploadError` gets the failure.
- `blocks` limits what `/` offers: `["paragraph", "heading1", "bulletList", ...]`.
- `surface="plain"` for a whole page, `"boxed"` (default) for a field in a form. `editable={false}` shows the content only.
- Use the `ref` (`focus`, `getHTML`, `setContent`, `clear`, `editor`) instead of reaching into Tiptap.
- Not in it yet: columns, wikilinks, mentions, emoji, link previews, file blocks, code highlight. Do not rebuild them in the app; ask to add them to the library.
- Made to fit: `extensions` (your own Tiptap extensions, keep the array stable), `slashItems` (your own blocks in the `/` menu), `renderBubbleMenu` (your tools over the selected text), `bubbleMenu` / `blockHandle` (turn them off), `autofocus`, `onReady(editor)`, `editorClassName`.
