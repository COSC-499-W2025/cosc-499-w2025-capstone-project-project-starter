# Weekly Navigation (Term 2)
- [Term 2 Week 2](#term-2-week-2--january-1218-2026)

## Will Tilden Personal Logs  //  Term 2 Week 2 – January 12–18, 2026

### Connection to Previous Week
- Nothing to connect to from last week.
- Great week overall; everyone made big contributions and the group worked well together.
- A big refactoring was completed by Liam (kudos to Liam) to get the team on track for the API requirements of milestone 2.

---

### Coding Tasks
- Completed feature number 28 under milestone 2: Customize and save the wording of a project used for a résumé item.
- Worked on Task #188 and Issue #181 from the project board/GitHub.
- Successfully started, completed, and merged the feature within this week.
- Submitted and merged PR (#182): <https://github.com/COSC-499-W2025/capstone-project-team-15/pull/182>
- Relevant links:
    - <https://github.com/COSC-499-W2025/capstone-project-team-15/issues/181>
    - <https://github.com/COSC-499-W2025/capstone-project-team-15/issues/188>

---

### Testing & Debugging Tasks
- Performed manual testing and ran test cases on my own PR (#182).
- Conducted testing and review of Liam's PR (#180).
- Performed manual testing and ran test cases for Rylan's PR (#190).

---

### Reviewing & Collaboration Tasks
- Reviewed Liam's PR (#180): <https://github.com/COSC-499-W2025/capstone-project-team-15/pull/180>
- Maintained high collegiality with the team throughout the week.
- Reviewed Rylan's PR (#190): <https://github.com/COSC-499-W2025/capstone-project-team-15/pull/190>

---

### Issues or Blockers
- No blockers or issues to report from this week.
- Minor uncertainty regarding GitHub terminology (distinction between project board items and issues), so both were referenced for clarity.

---

### Plan for Next Week
- Work on Feature 26: Allow user to associate a portfolio image for a given project to use as the thumbnail.
- Potentially work on Feature 22: Recognize duplicate files and maintain only one in the system.

---

### Peer evaluation Term 2 Week 2
![Alt text](imgs/will_tilden_t2_w2.png)

---


# Personal logs of Will Tilden (from Week 14) as per the personal log format outlined in lecture slides

## Applicable date range
- Monday, December 1st to Sunday, December 7th

## Type of tasks I worked on
![Alt text](imgs/will_tilden_w14.png)

## Recap on your weeks goals

- Which features were yours in the project plan for this milestone?

    I did not complete a contirbution this week I got completely overwhelmed studying for a final exam that I have tomorrow so that is on me.

- Which tasks from the project board are associated with these features?

    n/a

- Among these tasks, which have you completed / in progress in the last 2 weeks?

    n/a

- Optional text: additional context that we should be aware of

     My fault I didn't contribute this week just have a couple exams very early in the exam period so got overwhelmed and let it slip. My fault. 

- Working on in the next sprint

    I'd like to work on the export to PDF and make it a lot more customizable and clean for the user to get exactly what they want presented on there I think that would be really fun and interesting to work on.

# Personal logs of Will Tilden (from Week 12) as per the personal log format outlined in lecture slides
# Personal logs of Will Tilden (from Week 13) as per the personal log format outlined in lecture slides

## Applicable date range
- Monday, November 24th to Sunday, November 30th

## Type of tasks I worked on
![Alt text](imgs/will_tilden_w13.png)

## Recap on your weeks goals

- Which features were yours in the project plan for this milestone?

    I had issue 130 which was to add functionality such that both the ML data and the LLM data would be included in the PDF export when applicable if the user consented to the use of the LLM to analyze their data. This involved changes to the main file, refactoring the export function in the pdf exporter file to be able to handle the response from the llm, as well as driving this development with additional tests.

- Which tasks from the project board are associated with these features?

    The associated issue is issue [COSC-499-W2025/capstone-project-team-15#130](https://github.com/COSC-499-W2025/capstone-project-team-15/issues/130)

- Among these tasks, which have you completed / in progress in the last 2 weeks?

    I started and compeleted this issue this week.

- Optional text: additional context that we should be aware of

     This I think was one of my strongest weeks and I am proud of that. I made a strong contribution, I added tests that drove my development, I made two reviews on other people's PR's and was the first reviewer on one of those, and helped to test some of my other teammates code as well.

- Working on in the next sprint

    I believe this is our last sprint before the winter break? I could be confused but if not I would like to work more on the pdf exporter as I found it quite fun and interesting. The exported PDF is currently clean and straightforward but there is a lot of room for improvement and customization / personalization to the particular user.

# Personal logs of Will Tilden (from Week 12) as per the personal log format outlined in lecture slides

## Applicable date range
- Monday, November 17th to Sunday, November 23rd

## Type of tasks I worked on
![Alt text](imgs/will_tilden_w12.png)

## Recap on your weeks goals

- Which features were yours in the project plan for this milestone?

    This week my contribution and associated issue was finding a way to automatically get the DB tables added to the DB container upon setup of the container. This required editing the docker-compose.yml and adding a script that would wait until the DB container was successfully running and ready for a connection, and then having the yml file trigger the create_tables script in order to have them added automatically upon building the containers. This brings us one step closer to a fully connect pipeline.

- Which tasks from the project board are associated with these features?

    The associated issue is issue [COSC-499-W2025/capstone-project-team-15#115](https://github.com/COSC-499-W2025/capstone-project-team-15/issues/115)

- Among these tasks, which have you completed / in progress in the last 2 weeks?

    This issue was completed and closed this week by me with some help from Cole.

- Optional text: additional context that we should be aware of

     N/A

- Working on in the next sprint

    I'll be working together with the guys to go over the whole pipeline, make sure that all the indiviual components are working properly, being well tested, and are connecting properly to create a full pipeline. Basically with it being the last week before milestone #1 is due, we will essentially be checking over everything to make sure it is all working properly and that nothing was missed, etc. So it will be a busy but fun week.

# Personal log of Will Tilden (from Week 10) as per the personal log format outlined in lecture slides

## Applicable date range
- Monday, November 3rd to Sunday, November 9th

## Type of tasks I worked on
![Alt text](imgs/will_tilden_w10.png)

## Recap on your weeks goals

- Which features were yours in the project plan for this milestone?

    I had issue 76 which was the updates to the docker files which I mostly compelted last week but forgot to update the read me doc as well as move the environment variable into an env as opposed to uploading them into the repo, so that is the switch that I made for this week were those two things which now that they are finished makes the issue closed and completed.

- Which tasks from the project board are associated with these features?

    From the project board issue #76 titled docker setup improvements.

- Among these tasks, which have you completed / in progress in the last 2 weeks?

    This issue was created last week and mostly completed last week but as I mentioned I forgot these two things and so now it is all done and can be marked closed and I'll be looking for my next task this following week. 

- Optional text: additional context that we should be aware of

     None for this week, group feels good, I think we'll have a bit of a busies few weeks after reading week just getting everything pulled together for milestone 1 but I think that this team will work well together towards getting everything put together on time. I'm looking forward to the challenge.

- Working on in the next sprint

    - I'll be working together with the whole team to piece together our pipeline and get it working to a point where we can run containers, upload a zip, pass to the parser and then the ML... etc. basically getting all of the individual components working together to a point where we can feel reasonably close to being complete milestone 1.

# Personal log of Will Tilden (from Week 8) as per the personal log format outlined in lecture slides

## Applicable date range
- Monday, October 20th to Sunday, October 26th

## Type of tasks I worked on
![Alt text](imgs/will_tilden_w8.png)

## Recap on your weeks goals

- Which features were yours in the project plan for this milestone?

    This week my feature was to setup all of the necessary docker files so that we are ready to run our app in a docker container when the time comes to begin running it and testing it. Right now it is instead setup to run a test file (which is the test file I used to make sure my docker files were working properly) just to ensure that it is all setup properly but once we're ready to run the app in a docker container, we now have all the files in place to be able to do that which is a helpful step towards milestone 1 completion.

- Which tasks from the project board are associated with these features?

    From the project board issue [COSC-499-W2025/capstone-project-team-15#62](https://github.com/COSC-499-W2025/capstone-project-team-15/issues/62) is the one that I completed this week with my pull request.

- Among these tasks, which have you completed / in progress in the last 2 weeks?

    This issue was created and completed by me this week.

- Optional text: additional context that we should be aware of

     None for this week, I felt I made a storng contirbution to an important part of getting the app going and it is good to have it done ✅
     
# Personal log of Will Tilden (from Week 7) as per the personal log format outlined in lecture slides

## Applicable date range
- Monday, October 13th to Sunday, October 19th

## Type of tasks I worked on
![Alt text](imgs/will_tilden_w7.png)

## Recap on your weeks goals

- Which features were yours in the project plan for this milestone?

    This week my feature was #1 in the milestone requirements which specifies to ensure that the user is asked for their consent before their data is analyzed so I added the functionality to prompt the user for their consent before we analyzed their data. And I added tests to ensure this functionality works properly. I also mistakenly forgot to pull in our team logs from week 6 which was last week. They were my responsibility and I did them on time, I just forgot to pull them into the branch so we got a zero so I am going to get those pulled in and see if I may still be able to get them marked because I don't want to have let my team down there.

- Which tasks from the project board are associated with these features?

    From the project board issue [COSC-499-W2025/capstone-project-team-15#41](https://github.com/COSC-499-W2025/capstone-project-team-15/issues/41) is associated with the obtaining of the users consent for data analysis that i mentioned. And the issue associated with pulling in last weeks team logs is issue[COSC-499-W2025/capstone-project-team-15#43](https://github.com/COSC-499-W2025/capstone-project-team-15/issues/43).

- Among these tasks, which have you completed / in progress in the last 2 weeks?

    Both have been completed this week and are merged in now and marked done.

- Optional text: additional context that we should be aware of

     My mistake forgetting to merge in the team logs was an honest one and I do feel bad for letting my team down there so I am really hoping that, now that they are merged in, that someone may be able to go back and review them again so we may get the marks 🙏🏻.

# Personal log of Will Tilden (from Week 6) as per the personal log format outlined in lecture slides

## Applicable date range
- Monday, October 6th to Sunday, October 12th

## Type of tasks I worked on
![Alt text](imgs/will_tilden_w6.png)

## Recap on your weeks goals

- Which features were yours in the project plan for this milestone?

    I did issue 27 which was a documanation update on the project proposal document, and also helped others with their PRs doing reviews and giving suggestions.

- Which tasks from the project board are associated with these features?

    Issue 27 and the associated PR were mine for this week.

- Among these tasks, which have you completed / in progress in the last 2 weeks?

    The issue was completed today and is done now so into coding next week.

- Optional text: additional context that we should be aware of

     N/A

# Personal log of Will Tilden (from Week 5) as per the personal log format outlined in lecture slides

## Applicable date range
- Monday, September 29th to Sunday, October 5th

## Type of tasks I worked on
![Alt text](imgs/will_tilden_w5.png)

## Recap on your weeks goals

- Which features were yours in the project plan for this milestone?

    I helped the team work on the DFD diagram.

- Which tasks from the project board are associated with these features?

    DFD Explanation is the name of the associated issue.

- Among these tasks, which have you completed / in progress in the last 2 weeks?

    We completed this one, the DFD explanation, as well as the system architecture diagram.

- Optional text: additional context that we should be aware of

     N/A

# Personal log of Will Tilden (from Week 4) as per the personal log format outlined in lecture slides

## Applicable date range
- Monday, September 22nd to Sunday, September 28th

## Type of tasks I worked on
![Alt text](imgs/will_tilden_w4.png)

## Recap on your weeks goals

- Which features were yours in the project plan for this milestone?

    I was working on the project proposal and the system architecture diagram along with the rest of the team which we finished well and on time.

- Which tasks from the project board are associated with these features?

    These features, the proposal and system architecture diagram, were recorded as issues in our github repository and have all team members listed on them as assignees.

- Among these tasks, which have you completed / in progress in the last 2 weeks?

    This week we completed both the project proposal and the system architecture diagram and next week we will move on to the data flow diagram.

- Optional text: additional context that we should be aware of

    Another good week with a good team! Looking forward to working with this team throughout the year.




# Personal log of Will Tilden (from Week 3)

## What went well

- Team seems to work well together so far similar mindset and determination to do well on the project
- We got along well not just as like a team but we can have fun together which I think is important for a long term project like this one

## What didn’t go well

- The requirements gathering activity, while I believe I understand the intetion behind it, didn't feel terribly useful just given that a lot of the time was spent repeating requirements back at each other that teams already had themselves, I think I would have preffered having requirements given to us and just getting on writing the code sooner personally

## Planning for the next cycle

- Clarify and solidify requirements to the point that they are ready to inform coding / building decisions
- Delegate roles and responsibilities as far as who should work on which part(s) of the app
- Develop a sprint structure and cycle of some kind to keep the team synchronized and organized in moving forward with the project at the right pace and in an organized fashion

![Alt text](imgs/will_tilden_w3.png)
