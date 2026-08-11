# Manual Testing

This page records the manual tests I carried out while building Kindelise. I
tested locally and on the deployed site where needed. Stripe was tested in test
mode.

The **Works** column shows whether the test passed. **Errors found** notes any
problems I came across and what was done to fix them.

| ID | Area | Manual test | Expected result | Works | Errors found | Now complete |
| --- | --- | --- | --- | :---: | --- | :---: |
| MT-01 | Registration | I registered with a new email address and a valid password. | One account and one unverified profile should be created. | Yes | None on the final check. | Yes |
| MT-02 | Authentication | I signed in, signed out and then tried to reopen a protected page. | Sign-in and sign-out should work, and protected pages should send signed-out users back to sign-in. | Yes | My account was not allowed into staff admin at first. I corrected the staff permission and tested it again. | Yes |
| MT-03 | Plans | I created a plan with a title, description, future date, capacity, public URL and place. | The plan should save once, appear in the plan list and open correctly. | Yes | The place and image did not fill in at first. I fixed the Fetch details flow and tested it again. | Yes |
| MT-04 | Plans | I cancelled one of my plans and checked it in the plan list, profile and plan page. | The plan should stay in the history, show as Cancelled and no longer allow people to join. | Yes | None on the final check. | Yes |
| MT-05 | Participation | I used another profile to join, leave and rejoin a plan while checking its capacity. | The joined count should stay correct and the plan should never go over capacity. | Yes | The details table needed a small CSS fix, but the join data was correct. | Yes |
| MT-06 | Plan metadata | I entered a public HTTPS URL, selected Fetch details and checked the form, card and plan page. | The place name and thumbnail should be added and shown on the plan. | Yes | The image and place name did not appear at first. I fixed how the metadata was saved and displayed. | Yes |
| MT-07 | Messaging | I opened another profile, selected Send Message and checked the conversation from both accounts. | The message should appear in order and only the two people in the conversation should see it. | Yes | The message bubbles and profile images were inconsistent at first. I fixed the styling and image loading. | Yes |
| MT-08 | AI draft editing | I tried Fix grammar and Improve clarity, then tested both Keep original and Use suggestion. | Each option should give a useful suggestion without sending the message automatically. | Yes | The two suggestions were too similar at first. I changed the prompts and tested both options again. | Yes |
| MT-09 | Notifications | I triggered a new message and a new plan join, checked the count and then opened each notification. | Each new event should add to the count, and opening it should mark it as read. | Yes | Notifications were not part of the first version. I added the count and read handling, then tested them. | Yes |
| MT-10 | Profile editing | I changed the name, title statement, biography, areas, interests, availability and profile image. | The changes should save and appear correctly on the private and public profile pages. | Yes | Images did not stay saved on the deployed site at first. I added Cloudinary storage and retested uploads. | Yes |
| MT-11 | Availability | I turned Free now on and off and checked the private profile, public profile and discovery filter. | The availability change should appear in all three places. | Yes | The toggle colours were inconsistent during styling. I corrected the on state and tested it again. | Yes |
| MT-12 | Staff verification | I verified a complete profile in admin, removed verification and checked its access each time. | Staff should be able to grant or remove verification, and gated features should follow that status. | Yes | Verification was read-only in admin at first. I added the staff action and retested it. | Yes |
| MT-13 | Discovery | I used several area and interest filters, tested Free now and then cleared all filters. | Only matching profiles should appear, and clearing should restore the full allowed list. | Yes | I found small problems with mobile spacing, selected colours and clearing filters. These were fixed and retested. | Yes |
| MT-14 | Safety | I reported a profile and message, blocked a profile and checked that reporting still worked afterwards. | Reports should stay private, and blocking should stop discovery and contact in both directions. | Yes | The report button did not match the warning style. I corrected the colour and border. | Yes |
| MT-15 | Premium payment | I opened Stripe Checkout in test mode, completed the £4.99 payment and returned to my account. | Stripe should take the test payment once, Kindelise should show Premium access and Explore should change to Cancel Premium. | Yes | Checkout first showed an unwanted trial screen, then the button did not update because two Stripe events arrived in the same second. I fixed both problems and tested the payment again. | Yes |
| MT-16 | Validation | I submitted the registration, profile, plan and message forms with missing or invalid information. | The forms should stay on the page, show clear errors and keep any safe information already entered. | Yes | Error messages showed unwanted bullets and a side line. I cleaned up the shared error styling. | Yes |
| MT-17 | Responsive layout | I checked the main pages and forms at desktop and mobile sizes. | Text and controls should stay readable and usable without unwanted page overflow. | Yes | I fixed message-page padding, discovery filter spacing and several image sizes during the mobile checks. | Yes |
| MT-18 | Access control | I tried other users' edit links, an unauthorised conversation and actions that were not available to the signed-in profile. | The request should be refused without changing data or showing private information. | Yes | None on the final check. | Yes |
| MT-19 | Premium cancellation | I selected Cancel Premium, opened the Stripe customer portal and cancelled the test subscription. | The correct Stripe subscription should open and the cancellation should be recorded without taking another payment. | Yes | None on the final check. | Yes |

## Completion Summary

- I recorded 19 end-to-end manual tests.
- All 19 passed after the fixes listed above.
- Automated tests are covered separately in the main README.
