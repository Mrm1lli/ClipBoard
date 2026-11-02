# Finish the review before submitting

The recording is done. The remaining requirement is a corrected CRM, not just a
working tool. These observations are from a read-only live check after recording;
your local database may already contain decisions for some of them. An unchanged
CRM field does not tell us whether you rejected its proposal.

## Review substantive changes first

1. **Marietta and Tiffin — billing-protected ownership changes.** Review the old
   parent and both financial fields. Each plan must create a new account under
   Bellhaven and set the OLD account's `chow_current_account` to the successor ID.
   Preserve the old parent's ID, billing history, AR, and other original fields.
   Do not directly re-parent either old billing account.
2. **Zanesville — wrong parent and outdated name.** The original account has zero
   revenue/AR, so the existing account can be renamed and assigned to Bellhaven.
3. **Missing accounts — Amberly Manor (Hudson, OH), Bellhaven at Union Square,
   and Bellhaven of Batavia.** Inspect the candidate records and addresses before
   approving creates. A shared name or city is insufficient evidence of identity.
   Carlisle has already been created; don't create another copy.
4. **Five duplicate groups — Monroe, Kettering, Owosso, Port Clinton, and Erie.**
   Open each proposed survivor option and verify its effects on every other record.
   Suggested survivors, subject to your review:

   | Group | Suggested existing survivor | Reason |
   |---|---|---|
   | Monroe | `001U1750VLVJAGG1S5` | Current Bellhaven name and parent; all candidates have zero billing balances. |
   | Kettering | `0016KTS1UAWBRXS09J` | Unparented nursing/rehab record; all three share the address and have zero balances. Evidence does not prove a unique survivor; document this conservative tie-break. |
   | Owosso | `001EGU7BMJ942ZTRE6` | Name/address/parent match and the website phone matches. |
   | Port Clinton | `001UELXDAKFRKB8932` | Current Bellhaven name and parent; competing record uses an older operator identity. |
   | Erie | `001CVBBCSDM7YHN220` | Current Bellhaven name and parent; also update care offerings to include Memory Care. |

   Approval marks only the other records Inactive and sets `duplicate_of_account`;
   it does not delete/merge them. These recommendations are not prior approvals.
5. **Ashtabula — physical address replaces a PO box.** Name, phone, and geography
   support identity despite the billing address difference. Review the source.
6. **Portsmouth — ZIP correction.** Compare the website and CRM ZIP before approving.
7. **Remaining name corrections — Sycamore Ridge, Ashland, Chagrin Falls, and
   The Arbors at Bellhaven–Dayton.** Review the displayed current/proposed names.
8. **Absent listings — Alliance, Coldwater, and Sandusky.** The plans mark Needs
   Review and append an explanatory note; they do not infer a new owner or close
   the facility. Sandusky's financial history and outstanding AR remain untouched.

## Cosmetic proposals

Several proposals only abbreviate addresses. You may reject these with a specific
note if the existing address is already equivalent. Kalamazoo and Saline are
legitimate examples if their plans contain no other correction. Existing decisions
should remain in the Rejected tab; don't delete the database to recreate them.

## Check the result

1. Review all substantive items in the app. Approve only the plans you believe are
   right; reject or investigate unresolved cases and explain the decision.
2. Inspect Applied, Approved, and Applying. Applied means the remote write was read
   back successfully. Approved/Applying may require investigation and an explicit
   retry using the full proposal ID; see README.
3. Stop the server with Ctrl+C, run `python -m bellhaven run` using the virtual
   environment's Python, and restart `python -m bellhaven serve`.
4. Applied fixes should not return as pending. Identical rejected proposals should
   remain rejected. New evidence can require a new review.
5. Verify the important accounts in the CRM browser. Ask for an independent
   read-only check once your substantive review is complete.
6. Preserve `data/review.sqlite3` and `data/runs/` locally. Do not commit credentials
   or CRM snapshots. Submit the code link, working video link, honest time spent,
   and updated half-page writeup.
