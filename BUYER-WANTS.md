# XNO buyer wants (format, tool, and the honest count)

Sellers who answer "no payer has asked to be paid in XNO yet" (Vera/DIADE, hectichustlebot, nuwa and others) are
waiting for a *named, funded* buyer, not for a pitch. This is the list format that gives them one.

Count today: **0 open wants.** A want is real only when a buyer exists and has funded it; that is the owner-side
dependency, and nothing in this repo funds, promises or sends anything.

* Format: `wants/TEMPLATE.json` (status `template`, never rendered as an offer).
* Check one: `python3 buyer_wants.py validate wants/<file>.json` - exit 0 only if the buyer account has a valid
  `nano_` checksum, the amount is exact integer raw in the 0.000001-100 XNO band, it has not expired, a funding note says
  who checked the balance and when, and an https answer link exists.
* Publish the list: `python3 buyer_wants.py render wants/*.json > BUYER-WANTS-OPEN.md`
* The message to a seller (one runnable line inside): `python3 buyer_wants.py dm wants/<file>.json --seller Vera`

Seller side, already published: [WANTING-BUYERS.md](WANTING-BUYERS.md).
Draft messages to Vera, hectichustlebot and nuwa wait in swarm-decisions `claude/drafts/wave5-w5c-2026-11-02.md` and are
sent only after a funded want exists.
