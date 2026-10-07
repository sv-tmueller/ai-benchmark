## Story 1: Report a Hardware Issue

**User statement** — As an employee at Harborline Logistics, I want to report a faulty hardware device through the Service Catalog, so that the End User Computing team receives a correctly classified and prioritized incident without me having to call the service desk.

#### Item configuration

- **Type / classification:** Record Producer, target table **Incident [incident]**.
- **Placement:** Category **Help and Support > Report an Issue**, published to the **Employee Center** (primary) and the legacy **Service Portal** "Get Help" widget for shop-floor kiosk users.
- **Variable set:** `har_hw_report_vars` (shared definition, reused by Story 2's sibling producer).

| Variable name | Type | Label | Mandatory | Qualifiers / notes |
|---|---|---|---|---|
| `device_type` | Select Box | What kind of device | Yes | Choices: Laptop, Desktop workstation, Docking station, Printer, Mobile device, Other peripheral |
| `asset_tag` | String | Asset tag | Yes | Validation enforces format `HAR-#####` (uppercase); help text links to "Where to find your asset tag" |
| `location` | Reference | Where are you located | Yes | Table: Location [cmdb_location], filtered to active Harborline facilities |
| `impacted_service` | Reference | Affected business service | No | Table: Service Offering [service_offering] |
| `impact_level` | Select Box | Business impact | Yes | Choices: Site unable to operate, Team degraded, Individual inconvenience |
| `description` | Multiline Text | Describe the fault | Yes | Placeholder prompts for symptom, onset time, and any error codes |

- **Submission behavior:** Inserts an incident with `caller_id` = submitting user, `category` = Hardware, `urgency` derived from `impact_level` (Site unable to operate → 1-High, Team degraded → 2-Medium, Individual inconvenience → 3-Low), and priority computed by the standard urgency × impact matrix. The submitter is redirected to the Ticket Confirmation page showing the new INC number and expected response time.

**Fulfillment expectation:** Incidents land in the **End User Computing** queue (producer default assignment group). Technicians may retarget to **Network Operations** when the fault proves to be dock or network infrastructure. Initial-response target: 4 business hours.

#### Acceptance Criteria

```gherkin
Feature: Report a Hardware Issue catalog item
  Employees and contractors at Harborline Logistics report faulty
  hardware through the Employee Center and receive a correctly
  classified, prioritized incident in the End User Computing queue.

  Scenario: Happy-path submission creates a correctly populated incident
    Given Elodie Marsh (contractor, CC-2400 Warehouse Operations) is on the
      "Report a Hardware Issue" producer in the Employee Center
    When she submits the form with device_type "Docking station",
      asset_tag "HAR-48291", location "Chicago Distribution Center",
      impact_level "Team degraded", and description
      "Left-side USB ports stopped recognizing the scanner yesterday morning"
    Then a new incident is created with caller "Elodie Marsh",
      category "Hardware", urgency "2 - Medium", priority "Moderate",
      and assignment group "End User Computing"
    And Elodie sees the Ticket Confirmation page showing the new INC number
    And the incident appears in her My Tickets list with status "New"

  Scenario: Missing mandatory fields block submission
    Given Marcus Webb has filled in device_type "Printer" and description
      "Paper jams on tray 2" but left asset_tag blank and impact_level unselected
    When he presses Submit
    Then the form does not submit
    And inline validation flags "Asset tag" and "Business impact" as mandatory
    And no incident record is created

  Scenario: Malformed asset tag guides the user to the correct format
    Given Marcus Webb enters asset_tag "har-99"
    When he tries to submit the form
    Then validation rejects the value with the message
      "Enter the asset tag in HAR-##### format"
    And submission stays blocked until a compliant tag is entered
```

---

## Story 2: Report a Software or Application Issue

**User statement** — As a freight analytics contractor, I want to report a failing application or connectivity problem through the Service Catalog, so that my issue is routed to the right support team — Network Operations for connections, End User Computing for applications — on the first attempt.

#### Item configuration

- **Type / classification:** Record Producer, target table **Incident [incident]**.
- **Placement:** Category **Help and Support > Report an Issue**, published to the **Employee Center** and the **Service Portal** "Get Help" widget.
- **Variable set:** shares the org-standard styling with `har_hw_report_vars` but defines its own fields.

| Variable name | Type | Label | Mandatory | Qualifiers / notes |
|---|---|---|---|---|
| `application_area` | Select Box | Which area is affected | Yes | Choices: Email & Collaboration, Finance ERP (SAP), Customer CRM, VPN & Remote Access, Printing & Scan |
| `affected_application` | Reference | Which application | Yes | Table: Service Offering [service_offering], filtered to offerings owned by Enterprise Applications |
| `connectivity_symptoms` | Yes/No | Is it connection-related | Yes | Drives routing (see below) |
| `device_asset_tag` | String | Your device asset tag | No | Same `HAR-#####` validation as Story 1 |
| `impact_level` | Select Box | Business impact | Yes | Same choices as Story 1 |
| `description` | Multiline Text | What went wrong | Yes | Placeholder prompts for error message and reproduction steps |

- **Submission behavior:** Inserts an incident with `caller_id` = submitting user, `category` = Software, urgency derived from `impact_level` exactly as in Story 1, and `subcategory` copied from `application_area`. The submitter is redirected to the Ticket Confirmation page showing the INC number.

**Fulfillment expectation:** Routing rule on insertion — `connectivity_symptoms = Yes` assigns the incident to **Network Operations**; otherwise it goes to the **End User Computing** applications desk. Priority derives from the same urgency × impact matrix. Initial-response target: 4 business hours.

#### Acceptance Criteria

```gherkin
Feature: Report a Software or Application Issue catalog item
  Contractors and employees report software faults through the
  Employee Center and the incident is routed to Network Operations
  or End User Computing according to the connectivity answer.

  Scenario: Happy-path submission creates a correctly populated incident
    Given Tomás Ferreira (contractor, CC-3200 Commercial Sales) opens the
      "Report a Software or Application Issue" producer in the Employee Center
    When he submits the form with application_area "Finance ERP (SAP)",
      affected_application "Freight Billing SAP module",
      connectivity_symptoms "No", impact_level "Individual inconvenience",
      and description "Invoice void action throws error FIN-2041"
    Then a new incident is created with caller "Tomás Ferreira",
      category "Software", subcategory "Finance ERP (SAP)",
      urgency "3 - Low", priority "Low",
      and assignment group "End User Computing"
    And Tomás sees the Ticket Confirmation page showing the new INC number

  Scenario Outline: Routing follows the connectivity answer
    Given <actor> has submitted a software issue report with
      connectivity_symptoms <answer>
    When the incident is inserted
    Then the incident is assigned to <expected group>

    Examples:
      | actor             | answer | expected group         |
      | Priya Nair        | Yes    | Network Operations     |
      | Tomás Ferreira    | No     | End User Computing     |

  Scenario: Unanswered mandatory fields block submission
    Given Priya Nair chose application_area "VPN & Remote Access" but left
      affected_application blank and connectivity_symptoms unanswered
    When she presses Submit
    Then the form does not submit
    And inline validation flags "Which application" and
      "Is it connection-related" as mandatory
    And no incident record is created
```

---

## Story 3: Order a Standard Laptop

**User statement** — As a warehouse shift manager, I want to order standard laptops for my incoming team members through the Service Catalog, so that procurement prepares the purchase and IT provisions and hands over the machines without me chasing three departments by email.

#### Item configuration

- **Type / classification:** Traditional **catalog item** (not a record producer) on **sc_cat_item**; fulfilment produces a REQ (**sc_request**) with one RITM (**sc_req_item**) per submission.
- **Placement:** Category **Services > Hardware**, published to the **Employee Center** (people-leader audience).
- **Estimated price:** shown in-cart from variable pricing (Latitude USD 1,190 · ThinkPad USD 1,210 · EliteBook USD 1,230; accessories priced individually).

| Variable name | Type | Label | Mandatory | Qualifiers / notes |
|---|---|---|---|---|
| `laptop_model` | Select Box | Standard model | Yes | Choices: Dell Latitude 5450, Lenovo ThinkPad T14 Gen 5, HP EliteBook 840 G11 — all ships with the Harborline standard fleet image |
| `quantity` | Integer | Quantity | Yes | Default 1, minimum 1, maximum 5 |
| `accessories` | List Collector | Accessories | No | Choices: Docking station, 24-inch external monitor, Noise-cancelling headset, Laptop carry bag |
| `needed_by` | Date | Needed by | Yes | Must be at least 5 business days in the future |
| `ship_to_location` | Reference | Ship to location | Yes | Table: Location [cmdb_location], active Harborline facilities |
| `cost_center` | Reference | Charge to cost center | Yes | Filtered to cost centers belonging to the submitter's department |
| `business_justification` | Multiline Text | Justification | Conditional | Mandatory when `quantity` > 1 |

- **Submission behavior:** Cart checkout creates a REQ charged to `cost_center` with the estimated price, and one RITM carrying all variable values. The requester sees the order in **My Orders** with status Pending Approval.

#### Flow description (RITM-level approval + two strictly sequential tasks)

Implemented as a Flow Designer flow triggered on RITM creation for this item:

1. **RITM-level approval:** An **Ask for Approval** activity addresses the approver dynamically via a manager lookup (`requester.sys_manager`) — never a static group. **Reject** sets the RITM to **Closed Incomplete**, terminates the flow so no catalog task is ever created, and notifies the requester with the manager's name and rejection comment. **Approve** advances the flow.
2. **Sequential Task A:** On approval, one catalog task **"Reserve stock and prepare purchase order"** is created for **Procurement Services**, due 2 business days after approval. The flow waits until this task reaches **Closed Complete**; nothing else runs meanwhile.
3. **Sequential Task B:** Only after Task A closes, the second catalog task **"Pre-stage, configure, and arrange hand-over"** is created for **End User Computing**, due 3 business days. Closing Task B as Closed Complete sets the RITM to **Closed Complete**.

The two tasks MUST run strictly sequentially — never in parallel. Overall SLA posture: RITM resolution within 5 business days of approval (Task A ≤ 2 bd, Task B ≤ 3 bd).

#### Acceptance Criteria

```gherkin
Feature: Order a Standard Laptop catalog item
  Managers order standard laptops; the requester's manager approves on
  the RITM, Procurement Services reserves stock, and End User Computing
  configures and hands over the machine — strictly in that sequence.

  Scenario: Submission creates a REQ, a RITM, and routes approval to the requester's manager
    Given Dana Kovac (Shift Manager, Rotterdam Port Terminal) submits
      "Order a Standard Laptop" with laptop_model "Lenovo ThinkPad T14 Gen 5",
      quantity "2", accessories "Docking station, Noise-cancelling headset",
      needed_by ten business days ahead, ship_to_location
      "Rotterdam Port Terminal", cost_center "CC-2400 Warehouse Operations",
      and business_justification "Two new shift supervisors onboard November 16"
    Then a REQ is created charged to "CC-2400 Warehouse Operations"
      with the estimated price for 2 units plus accessories
    And one RITM is created under the REQ holding the same variable values
    And the RITM is Pending Approval with an approval assigned to
      Renzo Bianchi, Dana's manager, resolved by the dynamic manager lookup
    And no catalog task exists on the RITM

  Scenario: Manager approval starts Task A only
    Given the laptop RITM is Pending Approval with no catalog tasks
    When Renzo Bianchi approves the RITM approval
    Then the RITM moves to Work in Progress
    And catalog task "Reserve stock and prepare purchase order" is created
      for Procurement Services with a 2-business-day due date
    And no second catalog task exists

  Scenario: Task A reaching Closed Complete unlocks Task B
    Given Task A "Reserve stock and prepare purchase order" is Active
      and Task B does not exist
    When Procurement Services sets Task A to Closed Complete with work notes
      "PO 45012 issued; 2 ThinkPads reserved in Rotterdam depot cage"
    Then catalog task "Pre-stage, configure, and arrange hand-over" is created
      for End User Computing with a 3-business-day due date

  Scenario: Both tasks closing completes the RITM
    Given Task A is Closed Complete and Task B
      "Pre-stage, configure, and arrange hand-over" is Active
    When End User Computing sets Task B to Closed Complete with work notes
      "Both units imaged, encrypted, and handed to Dana at the Rotterdam helpdesk"
    Then the RITM state becomes Closed Complete
    And Dana sees the fulfilled order in My Orders

  Scenario: Manager rejection terminates the flow with no orphaned tasks
    Given the laptop RITM is Pending Approval and no catalog task exists
    When Renzo Bianchi rejects the approval with comment
      "Headcount freeze — revisit Q1"
    Then the RITM state becomes Closed Incomplete
    And no SCTASK was ever created
    And Dana receives a rejection notification naming Renzo Bianchi
      and quoting his comment

  Scenario: Multi-unit orders require a written justification
    Given Dana sets quantity "3" and leaves business_justification blank
    When she tries to add the item to the cart
    Then the form blocks submission with the message
      "Justification is required when ordering more than one unit"

  Scenario: Needed-by dates closer than 5 business days are refused
    Given Dana sets needed_by to the coming Thursday, 3 business days away
    When she tries to submit the order
    Then validation refuses the date with the message
      "Needed-by must be at least 5 business days from today"
```

---

## Story 4: Request a Software License

**User statement** — As a finance analyst, I want to request a named or shared license for a tracked software product through the Service Catalog, so that licensing compliance is checked by Software Asset Management before End User Computing installs and grants me access.

#### Item configuration

- **Type / classification:** Traditional **catalog item** on **sc_cat_item**; fulfilment produces a REQ with one RITM per submission.
- **Placement:** Category **Services > Software**, published to the **Employee Center** and the **Service Portal**.

| Variable name | Type | Label | Mandatory | Qualifiers / notes |
|---|---|---|---|---|
| `software_title` | Reference | Software requested | Yes | Table: Software Product [cmdb_software_product], filtered to active tracked products |
| `license_type` | Select Box | License type | Yes | Choices: Named user, Shared (concurrency pool) |
| `licensed_users` | List Collector | Users to license | Conditional | Mandatory when `license_type` = Named user; references active Harborline users |
| `term` | Select Box | Subscription term | Yes | Choices: 12 months, 24 months |
| `business_justification` | Multiline Text | Why is it needed | Yes | Reviewed by the approver and Software Asset Management |
| `cost_center` | Reference | Charge to cost center | Yes | Filtered to cost centers belonging to the submitter's department |

- **Submission behavior:** Checkout creates a REQ charged to `cost_center` and one RITM holding all variable values. The requester sees the request in **My Requests** with status Pending Approval.

#### Flow description (RITM-level approval + two strictly sequential tasks)

Same flow shape as Story 3, differing in groups and specifics:

1. **RITM-level approval:** Dynamic manager lookup resolves the approver to the requester's manager (example: Sofia Lindqvist's request routes to **Wei Chen**). **Reject** sets the RITM to **Closed Incomplete**, prevents any downstream task from being created, and notifies the requester. **Approve** advances the flow.
2. **Sequential Task A:** On approval, catalog task **"Entitlement and compliance check"** is created for **Software Asset Management**, due 1 business day after approval. The flow waits until it reaches **Closed Complete**.
3. **Sequential Task B:** Only after Task A closes, catalog task **"Install and grant access"** is created for **End User Computing**, due 2 business days. Closing Task B as Closed Complete sets the RITM to **Closed Complete**.

The two tasks MUST run strictly sequentially — never in parallel. Overall SLA posture: RITM resolution within 3 business days of approval (Task A ≤ 1 bd, Task B ≤ 2 bd).

#### Acceptance Criteria

```gherkin
Feature: Request a Software License catalog item
  Analysts request licenses; the requester's manager approves on the
  RITM, Software Asset Management verifies entitlement, and End User
  Computing installs and grants access — strictly in that sequence.

  Scenario: Happy-path submission creates a REQ and RITM awaiting manager approval
    Given Sofia Lindqvist (Financial Analyst, Singapore Regional HQ) submits
      "Request a Software License" with software_title "Tableau Creator",
      license_type "Named user", licensed_users "Sofia Lindqvist",
      term "12 months", cost_center "CC-3200 Commercial Sales",
      and business_justification "Monthly margin dashboards move off Excel in December"
    Then a REQ is created charged to "CC-3200 Commercial Sales"
    And one RITM is created under the REQ holding the same variable values
    And the RITM is Pending Approval with an approval assigned to Wei Chen,
      Sofia's manager, resolved by the dynamic manager lookup
    And no catalog task exists on the RITM

  Scenario: Named-user selections require the user roster
    Given Sofia picked license_type "Named user" and left licensed_users empty
    When she tries to submit the request
    Then the form blocks submission with the message
      "List at least one user for a named-user license"

  Scenario Outline: The entitlement check reflects the license type
    Given Wei Chen approved the RITM and Task A
      "Entitlement and compliance check" is Active for Software Asset Management
    When the SAM analyst opens Task A
    Then the task presents <evidence> drawn from the RITM variables
    And closing Task A as Closed Complete unlocks Task B
      "Install and grant access" for End User Computing

    Examples:
      | license_type                  | evidence                                   |
      | Named user                    | the roster of users from licensed_users    |
      | Shared (concurrency pool)     | the projected concurrent-demand figure     |

  Scenario: Both tasks closing completes the RITM
    Given Task A is Closed Complete and Task B "Install and grant access" is Active
    When End User Computing sets Task B to Closed Complete with work notes
      "Tableau Creator activated for sofia.lindqvist@harborline.com"
    Then the RITM state becomes Closed Complete
    And Sofia sees the fulfilled request in My Requests

  Scenario: Manager rejection terminates the flow with no orphaned tasks
    Given the license RITM is Pending Approval and no catalog task exists
    When Wei Chen rejects the approval with comment
      "Duplicate — team already holds shared seats"
    Then the RITM state becomes Closed Incomplete
    And no SCTASK was ever created
    And Sofia receives a rejection notification naming Wei Chen
      and quoting his comment
```

---

## Story 5: Log a Recurring IT Problem

**User statement** — As a problem manager, I want to log a recurring IT issue observed across multiple incidents through the Service Catalog, so that Problem Coordination receives a triage-ready problem record with the pattern, frequency, and related incidents already attached.

#### Item configuration

- **Type / classification:** Record Producer, target table **Problem [problem]**.
- **Placement:** Category **IT Operations > Continuous Improvement**, published to the **Employee Center** only, gated by user criteria restricting visibility to Problem Coordination members and holders of the problem coordinator role.

| Variable name | Type | Label | Mandatory | Qualifiers / notes |
|---|---|---|---|---|
| `short_description` | String | One-line summary | Yes | Maximum 160 characters |
| `detected_via` | Select Box | How was it detected | Yes | Choices: Trend analysis, Major incident review, Monitoring alert, Repeat user complaints |
| `affected_business_service` | Reference | Affected business service | Yes | Table: Service Offering [service_offering] |
| `recurrence_pattern` | Select Box | Recurrence pattern | Yes | Choices: Constant, Daily peaks, Weekly peak, Month-end cluster, Intermittent |
| `occurrences_recent` | Integer | Occurrences in the last 30 days | Yes | Minimum accepted value 2 |
| `related_incidents` | List Collector | Known related INCs | No | Table: Incident [incident], filtered to records involving the selected service |
| `suspected_cause` | Multiline Text | Suspected cause | No | Free text for hypotheses and evidence pointers |

- **Submission behavior:** Creates a problem record with `short_description` composed from the summary, `assigned_to` group **Problem Coordination**, and a problem statement assembled from the pattern, detection source, and occurrence count. Selected related incidents are linked on the record. The submitter sees the confirmation page with the new PRB number.

**Fulfillment expectation:** Triaged handover — Problem Coordination acknowledges and begins investigation within 1 business day; the record stays in state New until triage confirms the problem statement.

#### Acceptance Criteria

```gherkin
Feature: Log a Recurring IT Problem catalog item
  Problem managers log recurring issues through the Employee Center
  and Problem Coordination receives a triage-ready problem record
  with pattern, frequency, and linked incidents.

  Scenario: Happy-path submission creates a triage-ready problem record
    Given Farrah Aziz (Problem Manager, CC-1010 Corporate IT) opens the
      "Log a Recurring IT Problem" producer in the Employee Center
    When she submits the form with short_description
      "Scanner disconnects spike every weekday 08:00-09:00",
      detected_via "Repeat user complaints",
      affected_business_service "Warehouse scanning service",
      recurrence_pattern "Daily peaks", occurrences_recent "14",
      related_incidents "INC0011042, INC0011088, INC0011130",
      and suspected_cause "Suspect DHCP lease churn on VLAN 40"
    Then a problem record is created with assignment group
      "Problem Coordination" and state New
    And the problem statement cites the pattern "Daily peaks",
      the detection source, and 14 occurrences in 30 days
    And the three listed incidents are linked to the problem record
    And Farrah sees the confirmation page showing the new PRB number

  Scenario: Fewer than two occurrences are refused
    Given Farrah enters occurrences_recent "1"
    When she tries to submit the form
    Then validation refuses the value with the message
      "Describe at least 2 occurrences in the last 30 days"
    And no problem record is created

  Scenario: The item is invisible outside the intended audience
    Given Marcus Webb, a warehouse associate without the problem
      coordinator role, browses the Employee Center catalogs
    When he views the "IT Operations" category
    Then "Log a Recurring IT Problem" is not offered to him
    And direct navigation to the producer URL shows an access-denied page
```
