// Rebuild the README guestbook from labelled issues. User-submitted text is untrusted.
const fs = require("fs");

const MAX_ENTRIES = 8;
const MAX_LEN = 180;

function clean(body) {
  let text = String(body || "");
  const match = text.match(/### Your message\s+([\s\S]*)/);
  if (match) text = match[1];

  text = text
    .replace(/_No response_/g, "")
    .replace(/https?:\/\/\S+/gi, "link")
    .replace(/www\.\S+/gi, "link")
    .replace(/[<>\[\]()|*_`~#\\{}=]/g, "")
    .replace(/@/g, "＠")
    .replace(/\s+/g, " ")
    .trim();

  const chars = [...text];
  if (chars.length > MAX_LEN) text = chars.slice(0, MAX_LEN - 1).join("") + "…";
  return text || "Thanks for visiting ✦";
}

module.exports = async ({ github, context }) => {
  const { owner, repo } = context.repo;
  const issues = await github.paginate(github.rest.issues.listForRepo, {
    owner, repo, labels: "guestbook", state: "all", per_page: 100,
  });

  const rows = issues
    .filter((issue) =>
      !issue.pull_request &&
      /^[A-Za-z0-9-]{1,39}$/.test(issue.user.login) &&
      issue.user.type === "User" &&
      !issue.locked
    )
    .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
    .slice(0, MAX_ENTRIES)
    .map((issue) => {
      const login = issue.user.login;
      const date = new Date(issue.created_at).toISOString().slice(0, 10);
      return `| <img src="https://github.com/${login}.png?size=48" width="28" alt="${login}" /> | [${login}](https://github.com/${login}) | ${clean(issue.body)} | ${date} |`;
    });

  const block = rows.length
    ? ["| | Visitor | Message | Date |", "|:-:|---|---|---|", ...rows].join("\n")
    : '<p align="center"><i>No entries yet. Be the first to sign ✦</i></p>';

  const readme = fs.readFileSync("README.md", "utf8");
  const start = "<!-- GUESTBOOK:START -->";
  const end = "<!-- GUESTBOOK:END -->";
  const a = readme.indexOf(start);
  const b = readme.indexOf(end);
  if (a === -1 || b === -1 || b < a) throw new Error("Guestbook markers are missing or out of order");

  const next = readme.slice(0, a + start.length) + "\n" + block + "\n" + readme.slice(b);
  fs.writeFileSync("README.md", next);

  const issue = context.payload.issue;
  if (
    context.eventName === "issues" &&
    issue &&
    issue.labels.some((label) => label.name === "guestbook") &&
    context.payload.action === "opened"
  ) {
    await github.rest.issues.createComment({
      owner, repo, issue_number: issue.number,
      body: `Thanks for signing the guestbook! Your message has been added to https://github.com/${owner}`,
    });
    await github.rest.issues.update({
      owner, repo, issue_number: issue.number, state: "closed", state_reason: "completed",
    });
  }
};
