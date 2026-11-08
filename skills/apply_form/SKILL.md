# Skill: Job application form assistance

> Use this skill to prepare, fill, and verify supported fields on a job application site.
> Triggers: job application, apply for a job, fill a form, save resume, 网申、投递、填表、保存简历、改岗

The user leads the application. The assistant prepares copy-ready text, fills straightforward fields when the values are known, and checks what was saved. The user handles login, CAPTCHA, dynamic or unclear fields, and final submission.

## Before starting

1. Confirm the target role and any application limits.
2. Confirm which resume file to use.
3. Check that your workspace provides the browser tools required by this workflow. Example commands such as `browser.dump` and `browser.save` require a separate browser integration.

## Workflow

1. Inspect labels, current values, and disabled fields before writing.
2. Fill the static text fields in the relevant section. Leave uncertain values blank and report them.
3. Identify a file input by its accepted file types and surrounding section before uploading. Verify that the displayed filename changes as expected.
4. Guide the user through date pickers, dependent dropdowns, and adding or removing repeated sections. Let the user review any required privacy notice before continuing.
5. Verify a save through the write response or a safe readback. When inspecting the response, look for both HTTP success and the application's success marker. Reload only when the site has saved the state and a reload is safe.
6. Record which fields were verified and which still need user input. Stop after two consecutive failures and write a checkpoint.

The user performs final submission.
