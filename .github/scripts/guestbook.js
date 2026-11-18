// Rebuild the README guestbook from labelled issues.
// User-submitted content is untrusted and must be sanitized.

const fs = require("fs");

const MAX_ENTRIES = 8;
const MAX_LEN = 180;

const START_MARKER = "<!-- GUESTBOOK:START -->";
const END_MARKER = "<!-- GUESTBOOK:END -->";

function clean(body) {
  let text = String(body || "");

  // Extract only the answer under the intended issue-template field.
  const match = text.match(
    /(?:^|\n)### Your message\s*\n([\s\S]*?)(?=\n###\s|$)/i
  );

  if (match) {
    text = match[1];
  }

  text = text
    // Remove GitHub's empty-response placeholder.
    .replace(/_No response_/gi, "")

    // Prevent external links from being rendered in the table.
    .replace(/https?:\/\/\S+/gi, "link")
    .replace(/www\.\S+/gi, "link")

    // Remove Markdown and HTML-sensitive syntax.
    .replace(/[<>\[\]()|*_`~#\\{}=!]/g, "")

    // Avoid mentions and control characters.
    .replace(/@/g, "＠")
    .replace(/[\u0000-\u001F\u007F]/g, " ")

    // Keep each message on one table row.
    .replace(/\s+/g, " ")
    .trim();

  const chars = [...text];

  if (chars.length > MAX_LEN) {
    text = chars.slice(0, MAX_LEN - 1).join("") + "…";
  }

  return text || "Thanks for visiting ✦";
}

function isValidVisitor(issue) {
  const user = issue?.user;

  return Boolean(
    !issue.pull_request &&
    user &&
    user.type === "User" &&
    typeof user.login === "string" &&
    /^[A-Za-z0-9-]{1,39}$/.test(user.login) &&
    !issue.locked
  );
}

function buildGuestbook(issues) {
  const rows = issues
    .filter(isValidVisitor)
    .sort(
      (a, b) =>
        new Date(b.created_at).getTime() -
        new Date(a.created_at).getTime()
    )
    .slice(0, MAX_ENTRIES)
    .map((issue) => {
      const login = issue.user.login;
      const date = new Date(issue.created_at)
        .toISOString()
        .slice(0, 10);

      return (
        `| <img src="https://github.com/${login}.png?size=48" ` +
        `width="28" alt="${login}" /> ` +
        `| [${login}](https://github.com/${login}) ` +
        `| ${clean(issue.body)} | ${date} |`
      );
    });

  if (!rows.length) {
    return (
      '<p align="center"><i>' +
      "No entries yet. Be the first to sign ✦" +
      "</i></p>"
    );
  }

  return [
    "| | Visitor | Message | Date |",
    "|:-:|---|---|---|",
    ...rows,
  ].join("\n");
}

function updateReadme(block) {
  const readme = fs.readFileSync("README.md", "utf8");

  const startCount = readme.split(START_MARKER).length - 1;
  const endCount = readme.split(END_MARKER).length - 1;

  if (startCount !== 1 || endCount !== 1) {
    throw new Error(
      "README must contain exactly one Guestbook start marker and one end marker."
    );
  }

  const startIndex = readme.indexOf(START_MARKER);
  const endIndex = readme.indexOf(END_MARKER);

  if (endIndex < startIndex) {
    throw new Error(
      "Guestbook markers are missing or out of order."
    );
  }

  const contentStart = startIndex + START_MARKER.length;

  const next =
    readme.slice(0, contentStart) +
    "\n" +
    block +
    "\n" +
    readme.slice(endIndex);

  if (next !== readme) {
    fs.writeFileSync("README.md", next, "utf8");
    console.log("Guestbook README updated.");
  } else {
    console.log("Guestbook is already up to date.");
  }
}

async function acknowledgeSubmission({
  github,
  owner,
  repo,
  issue,
}) {
  if (!issue) return;

  const isGuestbookIssue = (issue.labels || []).some(
    (label) => label.name === "guestbook"
  );

  if (!isGuestbookIssue) return;

  // Avoid duplicate acknowledgements if a workflow is retried.
  const comments = await github.paginate(
    github.rest.issues.listComments,
    {
      owner,
      repo,
      issue_number: issue.number,
      per_page: 100,
    }
  );

  const marker = "<!-- guestbook-thanks -->";

  const alreadyAcknowledged = comments.some(
    (comment) =>
      comment.user?.type === "Bot" &&
      comment.body?.includes(marker)
  );

  if (!alreadyAcknowledged) {
    await github.rest.issues.createComment({
      owner,
      repo,
      issue_number: issue.number,
      body:
        `Thanks for signing the guestbook! ` +
        `Your message has been added to https://github.com/${owner}\n\n` +
        marker,
    });
  }

  // Close only newly submitted guestbook issues.
  if (issue.state !== "closed") {
    await github.rest.issues.update({
      owner,
      repo,
      issue_number: issue.number,
      state: "closed",
      state_reason: "completed",
    });
  }
}

module.exports = async ({ github, context }) => {
  const { owner, repo } = context.repo;

  // Retrieve all issues carrying the Guestbook label.
  const issues = await github.paginate(
    github.rest.issues.listForRepo,
    {
      owner,
      repo,
      labels: "guestbook",
      state: "all",
      per_page: 100,
    }
  );

  // Rebuild the README section from the latest valid entries.
  const block = buildGuestbook(issues);
  updateReadme(block);

    // Acknowledge and close newly submitted Guestbook issues.
  if (
    context.eventName === "issues" &&
    (
      context.payload.action === "opened" ||
      (
        context.payload.action === "labeled" &&
        context.payload.label?.name === "guestbook"
      )
    )
  ) {
    await acknowledgeSubmission({
      github,
      owner,
      repo,
      issue: context.payload.issue,
    });
  }

  console.log(
    `Guestbook rebuild completed. ${Math.min(
      issues.filter(isValidVisitor).length,
      MAX_ENTRIES
    )} entries displayed.`
  );
};
