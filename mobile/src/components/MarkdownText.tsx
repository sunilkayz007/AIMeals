import { View, Text } from 'react-native';

// Lightweight markdown renderer — hand-rolled rather than a third-party
// library, since the Nutrition Coach's system prompt only ever produces
// a specific known subset: **bold**, ## headers, - bullet lists,
// 1. numbered lists, and plain paragraphs. No tables, links, images,
// code blocks, or nested lists to worry about.
//
// Re-parses the full text on every call, which is fine even during live
// streaming (the reveal loop re-renders as text grows) — for chat-length
// messages this is cheap, and it's the same approach production chat
// UIs generally take. Partial/incomplete markers (e.g. "**bold" not yet
// closed) will render as literal asterisks for a moment until the
// closing marker streams in — a normal, expected artifact of live
// markdown rendering, not a bug.

interface MarkdownTextProps {
  text: string;
  color: string;
  accentColor: string;
  fontSize?: number;
}

function renderInline(text: string, keyPrefix: string, color: string): React.ReactNode[] {
  const parts: React.ReactNode[] = [];
  const regex = /(\*\*(.+?)\*\*|\*(.+?)\*)/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  let i = 0;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }
    if (match[2] !== undefined) {
      parts.push(
        <Text key={`${keyPrefix}-b-${i++}`} style={{ fontWeight: '700', color }}>
          {match[2]}
        </Text>
      );
    } else if (match[3] !== undefined) {
      parts.push(
        <Text key={`${keyPrefix}-i-${i++}`} style={{ fontStyle: 'italic', color }}>
          {match[3]}
        </Text>
      );
    }
    lastIndex = regex.lastIndex;
  }
  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }
  return parts;
}

export default function MarkdownText({ text, color, accentColor, fontSize = 13 }: MarkdownTextProps) {
  const blocks = text.split(/\n\n+/).filter((b) => b.trim());

  return (
    <View>
      {blocks.map((block, bi) => {
        const lines = block.split('\n').filter((l) => l.trim());
        if (lines.length === 0) return null;

        // Header (## or ###)
        if (/^#{1,3}\s/.test(lines[0])) {
          const headerText = lines[0].replace(/^#{1,3}\s/, '');
          return (
            <Text
              key={`h-${bi}`}
              style={{
                fontSize: fontSize + 1,
                fontWeight: '700',
                color: accentColor,
                marginTop: bi > 0 ? 10 : 0,
                marginBottom: 4,
              }}
            >
              {renderInline(headerText, `h-${bi}`, accentColor)}
            </Text>
          );
        }

        const isBulletList = lines.every((l) => /^[-*]\s/.test(l.trim()));
        const isNumberedList = lines.every((l) => /^\d+\.\s/.test(l.trim()));

        if (isBulletList || isNumberedList) {
          return (
            <View key={`l-${bi}`} style={{ marginBottom: 8 }}>
              {lines.map((line, li) => {
                const content = line.trim().replace(/^([-*]|\d+\.)\s/, '');
                return (
                  <View
                    key={`li-${bi}-${li}`}
                    style={{ flexDirection: 'row', marginBottom: 3, paddingRight: 4 }}
                  >
                    <Text
                      style={{
                        fontSize,
                        color: accentColor,
                        fontWeight: '700',
                        marginRight: 6,
                        minWidth: isNumberedList ? 16 : undefined,
                      }}
                    >
                      {isNumberedList ? `${li + 1}.` : '•'}
                    </Text>
                    <Text style={{ fontSize, color, flex: 1, lineHeight: fontSize + 5 }}>
                      {renderInline(content, `li-${bi}-${li}`, color)}
                    </Text>
                  </View>
                );
              })}
            </View>
          );
        }

        // Plain paragraph
        return (
          <Text
            key={`p-${bi}`}
            style={{
              fontSize,
              color,
              lineHeight: fontSize + 6,
              marginBottom: bi < blocks.length - 1 ? 8 : 0,
            }}
          >
            {renderInline(lines.join(' '), `p-${bi}`, color)}
          </Text>
        );
      })}
    </View>
  );
}
