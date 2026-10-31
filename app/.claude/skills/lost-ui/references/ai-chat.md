# AI chat

`@danielsoaresf/lost-ui/ai-chat` has the pieces of a chat with an assistant. They need no SDK: a message is `{ id, role, parts }`, the same shape as the Vercel AI SDK `UIMessage`, so `useChat().messages` goes in as it is. Props of each component: [api/ai-chat](api/ai-chat.md).

## Pick the piece

| You need                                      | Use                                                                    |
| --------------------------------------------- | ---------------------------------------------------------------------- |
| the whole conversation, scrolling             | `ChatMessages` (messages, status, `footer` for the prompt, `empty`)    |
| one message                                   | `ChatMessage` (parts, avatar, actions, `renderText`, `renderPart`)     |
| the box to write in                           | `ChatPrompt` (send, stop, retry by `status`; files with `attachments`) |
| only the send / stop / retry button           | `ChatPromptSubmit`                                                     |
| the model's thinking                          | `ChatReasoning` (opens while streaming, closes after)                  |
| a tool call, with output and approval buttons | `ChatTool`                                                             |
| "Thinking…" text with a moving light          | `ChatShimmer`                                                          |
| starter or follow-up prompts                  | `ChatSuggestions` (`row` or `grid`)                                    |
| a file chip or thumbnail                      | `ChatAttachment`                                                       |
| a chat inside a modal, drawer or palette      | `ChatPalette` + `ChatMessages compact` + `ChatPrompt`                  |

## A chat screen with the Vercel AI SDK

```tsx
import {
  ChatMessages,
  ChatPrompt,
  ChatSuggestions,
  messageText,
} from "@danielsoaresf/lost-ui/ai-chat";

const { messages, status, sendMessage, stop, regenerate } = useChat();

<div className="flex h-dvh flex-col">
  <ChatMessages
    messages={messages}
    status={status}
    empty={
      <ChatSuggestions suggestions={["Plan a launch"]} onSelect={(text) => sendMessage({ text })} />
    }
    getActions={(message) =>
      message.role === "assistant"
        ? [
            {
              label: "Copy",
              icon: <CopyIcon />,
              onClick: () => void navigator.clipboard.writeText(messageText(message)),
            },
          ]
        : undefined
    }
    renderText={(text) => <Markdown>{text}</Markdown>}
    footer={
      <ChatPrompt
        status={status}
        onSubmit={(text) => sendMessage({ text })}
        onStop={stop}
        onReload={regenerate}
      />
    }
  />
</div>;
```

## Rules

- The list needs a parent with a height (`h-dvh`, `h-full`, a flex column): it scrolls inside it. Put the `ChatPrompt` in `footer` so the list leaves room for it.
- Pass `status` to `ChatMessages` and to `ChatPrompt`; the list shows the indicator on `submitted`, marks itself busy, and the prompt turns its button into stop / retry.
- Text is drawn as plain text. Pass `renderText` with the Markdown renderer of the app.
- Draw a part the library does not know, or an approval card, with `renderPart(part, context)`; return `undefined` to keep the default.
- `ChatTool` takes `actions` for approve / deny buttons; the app decides what they do.
- Texts (placeholder, button names) come from `LostI18nProvider`; set the language once at the root.
- Do not build a message bubble, a prompt textarea or an auto-scroll by hand.

## The whole screen: `AiChatPage`

`@danielsoaresf/lost-ui/templates/ai-chat/ai-chat-page` is the chat screen with the list of conversations (a drawer on a phone), the welcome with suggestions, the messages and the prompt. Give its parent a height. Props: [api/templates](api/templates.md).

```tsx
<AiChatPage
  conversations={conversations}
  activeConversationId={id}
  onSelectConversation={setId}
  onNewConversation={() => setId(null)}
  messages={messages}
  status={status}
  onSend={(text, files) => sendMessage({ text })}
  onStop={stop}
  onReload={regenerate}
  suggestions={["Plan a launch"]}
  renderText={(text) => <Markdown>{text}</Markdown>}
/>
```
