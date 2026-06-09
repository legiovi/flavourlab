# Installing the FlavourLab skill

## Claude Code (personal skills)
Copy the whole `flavourlab` folder into your skills directory:

```bash
cp -r flavourlab ~/.claude/skills/
```

Then in any Claude Code session just ask, e.g.:
- "What pairs with lamb?"
- "Give me a wine for grilled beef"
- "Generate a braised lamb and apricot recipe"
- "How do I make hollandaise?"

Claude will auto-invoke the skill (it reads SKILL.md) and run `flavourlab.py`.

## Requirements
- Python 3 (standard library only — no pip installs needed)

## Manual use
```bash
cd ~/.claude/skills/flavourlab
python3 flavourlab.py pairings strawberry
python3 flavourlab.py generate lamb --pair apricot --cuisine "Middle Eastern"
```
