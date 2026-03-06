# KRANK Weekly Update Instructions

## Google Sheet
The tracker sheet URL is stored in `krank.config`. Read the SHEET_URL from that file.

## Weekly Update Task
When asked to "update the site" or "weekly update":
1. Read the SHEET_URL and GID from krank.config
2. Download as CSV: https://docs.google.com/spreadsheets/d/13B2rtH047LOxc_NpcfIH_BdPKoTBvsRi/export?format=csv&gid=958170120
3. Parse CSV: header row is index 3, data starts at index 4; skip rows where col 1 starts with ▸ or is empty
4. For each celebrity, read from these 0-based column indices:
   - Name: 1
   - Latest Followers (M): 75
   - Latest Media (0–100): 77
   - Latest Brand (0–100): 79  ← store as brandDeals = score*20/100 so formula still works
   - Latest Fan Engagement (0–100): 81  → update fanActivity field
   - Latest Fan Vote (0–100): 83  → (reserved for future use)
   - Latest Search (0–100): 85  → update searchTrend field
5. Skip any field that is empty — only update fields with actual values
6. If followers = "N/A" or empty → set followers:null
7. Match to index.html by exact name (uppercase); known mismatches: KIM DO-YOUNG → KIM DO-YEONG
8. Update fields using regex replacements
9. git add index.html
10. git commit -m "Weekly update – [today's date]"
11. git push

## Notes
- Followers are in millions (5.2 = 5,200,000)
- Fan Activity score is 0–100
- Only update celebrities that have data filled in
