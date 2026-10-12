# Output

## Repo
https://github.com/juancolamendy/support_copilot/tree/main 

## Step 1. One line on how it works. Every ticket goes through the same fixed pipeline:
1. Check the description is present.
2. Extract the key terms with the LLM.
3. Detect the product area from ownership.json.
4. Look for an active incident in that area.
5. Search the knowledge base, keeping only approved, internal documents, and score the confidence.
6. Escalate if nothing is found. Otherwise draft a reply with the LLM.

The LLM is only used for extraction and drafting. All routing is deterministic code.

## Step 2. Run each ticket. 
`uv run python -m support_copilot.cli --ticket TCK-1001` (and 1002, 1003). It prints one JSON result, and the node-by-node trace goes to stderr.

## TCK-1001: "Patient cannot reset portal password"
- Path: knowledge base, so it was answered.
- Reason:
  - The area is patient-portal, and there is no active incident there (INC-2022 is resolved).
  - The best approved document is KB-101.
- Citations: KB-101.
- Draft response:
▎ Suggested instructions for the patient (per KB-101):
▎ 1. Open the most recent password-reset email you received.
▎ 2. Click the link in that email and follow the prompts to complete the reset.
▎ 3. Note that the link expires after 30 minutes. If it has expired, start a new reset from the portal sign-in page and use the newest email.

▎ Reminder for staff: never ask the patient for their password or set it on their behalf.

▎ The documentation does not detail the specific on-screen steps after clicking the link, so none are included here.

```json
{
  "status": "ok",
  "error_message": null,
  "escalate": false,
  "response": "Suggested instructions for the patient (per KB-101):\n\n1. Open the most recent password-reset email.\n2. Follow the link in that email to complete the reset.\n3. The link expires after 30 minutes. If it has expired, start a new reset from the portal sign-in page and use the newest email.\n\nNote for staff: never ask the patient for their password or set it on their behalf.\n\nThe documents don't cover what the reset page itself looks like or any further steps after following the link, so I haven't included any.",
  "citations": [
    {
      "source_id": "KB-101",
      "reason": "confidence 0.83"
    }
  ],
  "confidence_score": 0.83,
  "owner": null,
  "incident": null,
  "area": "patient-portal",
  "notes": []
}
```

### TCK-1002: "Portal invitation expired"

- Path: knowledge base, so it was answered.
- Reason:
  - The area is patient-portal and there is no active incident.
  - KB-103
  - Search also surfaces KB-102, which says invitations last 72 hours. It is deprecated, so the filter drops it before drafting or citing.
- Citations: KB-103. KB-102 never appears.
- Draft response:
▎ The original invitation can't be reused. Portal invitation links expire after 24 hours, and an expired link cannot be reused, so a new invitation needs to be sent. Steps: 1) Verify the patient's email address. 2) Go to Profile > Portal Access > Send New Invitation. [KB-103]
```{
  "status": "ok",
  "error_message": null,
  "escalate": false,
  "response": "The expired invitation can't be reused. Portal invitation links expire after 24 hours, so a link sent two days ago is no longer valid and a new invitation must be sent. Steps: 1) Verify the patient's email address. 2) Go to Profile > Portal Access > Send New Invitation. (Source: KB-103)",
  "citations": [
    {
      "source_id": "KB-103",
      "reason": "confidence 1.00"
    }
  ],
  "confidence_score": 1.0,
  "owner": null,
  "incident": null,
  "area": "patient-portal",
  "notes": []
}
```

## TCK-1003: "Available appointments are blank"

- Path: incident, so it stopped early.
- Reason:
  - The area is scheduling, and INC-2041 is active ("Appointment availability is intermittently returning no results for staff users", status investigating).
  - The flow stops there: no knowledge search and no drafted reply, so it doesn't contradict an ongoing outage.
- Citations: none, by design.
- Draft response: none (response is null). Instead the output links the incident (INC-2041) and the owner, Care Access Engineering, channel #help-care-access.
```{
  "status": "ok",
  "error_message": null,
  "escalate": true,
  "response": null,
  "citations": [],
  "confidence_score": null,
  "owner": {
    "area": "scheduling",
    "team": "Care Access Engineering",
    "escalation_channel": "#help-care-access"
  },
  "incident": {
    "id": "INC-2041",
    "area": "scheduling",
    "status": "investigating",
    "summary": "Appointment availability is intermittently returning no results for staff users.",
    "updated_at": "2026-09-21T16:35:00Z"
  },
  "area": "scheduling",
  "notes": []
}
```
