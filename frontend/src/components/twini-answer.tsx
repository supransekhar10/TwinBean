import { Fragment, type ReactNode } from "react";

function inlineMarkdown(text: string): ReactNode[] {
  const tokens = text.split(/(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\])/g);
  return tokens.filter(Boolean).map((token, index) => {
    if (token.startsWith("**") && token.endsWith("**")) {
      return <strong key={index}>{token.slice(2, -2)}</strong>;
    }
    if (token.startsWith("`") && token.endsWith("`")) {
      return <code key={index}>{token.slice(1, -1)}</code>;
    }
    if (token.startsWith("[") && token.endsWith("]")) {
      return <span className="twini-inline-citation" key={index}>{token.slice(1, -1)}</span>;
    }
    return <Fragment key={index}>{token}</Fragment>;
  });
}

function cells(line: string) {
  return line.trim().replace(/^\||\|$/g, "").split("|").map((cell) => cell.trim());
}

function isTableDivider(line: string) {
  return cells(line).every((cell) => /^:?-{3,}:?$/.test(cell));
}

export function TwiniAnswer({ content, compact = false }: { content: string; compact?: boolean }) {
  const lines = content.replace(/\r\n/g, "\n").split("\n");
  const blocks: ReactNode[] = [];

  for (let index = 0; index < lines.length;) {
    const line = lines[index].trim();
    if (!line) { index += 1; continue; }

    const heading = /^(#{1,3})\s+(.+)$/.exec(line);
    if (heading) {
      const level = Math.min(heading[1].length + 2, 5);
      const Tag = `h${level}` as "h3" | "h4" | "h5";
      blocks.push(<Tag key={`heading-${index}`}>{inlineMarkdown(heading[2])}</Tag>);
      index += 1;
      continue;
    }

    if (index + 1 < lines.length && line.includes("|") && isTableDivider(lines[index + 1])) {
      const headers = cells(line);
      const rows: string[][] = [];
      index += 2;
      while (index < lines.length && lines[index].trim().includes("|")) {
        rows.push(cells(lines[index]));
        index += 1;
      }
      blocks.push(compact ? (
        <div className="twini-answer-records" key={`table-${index}`}>
          {rows.map((row, rowIndex) => (
            <section aria-label={`Result ${rowIndex + 1}`} key={rowIndex}>
              {headers.map((header, cellIndex) => (
                <div key={cellIndex}>
                  <strong>{inlineMarkdown(header)}</strong>
                  <p>{inlineMarkdown(row[cellIndex] ?? "Not provided")}</p>
                </div>
              ))}
            </section>
          ))}
        </div>
      ) : (
        <div className="twini-answer-table-wrap" key={`table-${index}`}>
          <table><thead><tr>{headers.map((header, cellIndex) => <th key={cellIndex}>{inlineMarkdown(header)}</th>)}</tr></thead>
          <tbody>{rows.map((row, rowIndex) => <tr key={rowIndex}>{headers.map((_, cellIndex) => <td key={cellIndex}>{inlineMarkdown(row[cellIndex] ?? "Not provided")}</td>)}</tr>)}</tbody></table>
        </div>
      ));
      continue;
    }

    const unordered = /^[-*]\s+(.+)$/.exec(line);
    const ordered = /^\d+[.)]\s+(.+)$/.exec(line);
    if (unordered || ordered) {
      const orderedList = Boolean(ordered);
      const items: string[] = [];
      while (index < lines.length) {
        const match = orderedList ? /^\d+[.)]\s+(.+)$/.exec(lines[index].trim()) : /^[-*]\s+(.+)$/.exec(lines[index].trim());
        if (!match) break;
        items.push(match[1]);
        index += 1;
      }
      const List = orderedList ? "ol" : "ul";
      blocks.push(<List key={`list-${index}`}>{items.map((item, itemIndex) => <li key={itemIndex}>{inlineMarkdown(item)}</li>)}</List>);
      continue;
    }

    const paragraph = [line];
    index += 1;
    while (index < lines.length && lines[index].trim() && !/^(#{1,3})\s+|^[-*]\s+|^\d+[.)]\s+/.test(lines[index].trim()) && !(index + 1 < lines.length && lines[index].includes("|") && isTableDivider(lines[index + 1]))) {
      paragraph.push(lines[index].trim());
      index += 1;
    }
    blocks.push(<p key={`paragraph-${index}`}>{inlineMarkdown(paragraph.join(" "))}</p>);
  }

  return <div className="twini-answer">{blocks}</div>;
}
