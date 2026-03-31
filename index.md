## Welcome to the SEE-Insight Research Team

![SEE-Insight logo](./images/Mag_eye.png)

The SEE-Insight Research Team is lead by [Dr. Dirk Colbry](http://www.dirk.colbry.com/) in the Department of Computational Mathematics, Science and Engineering at Michigan State University. 

We hold a weekly group meeting on Tuesdays 9:10\-10:00am ET (Spring 2026) which are open to the public.  Please email Dr. Colbry [colbrydi@msu.edu](mailto:colbrydi@msu.edu) if you would like to join us and he can send you the room locaiton, zoom coordinates and/or add you to our group email list.
 
### Problem Description
Low-cost imaging allow researchers who rely on visual observations to digitally record experiments, resulting in huge databases of images that can be reviewed and re-reviewed over time. “Scientific image understanding” is the process of extracting scientific measurements out of images. Since the information of interest within an image changes with each new research question there is no single “universal measurement” and no single software program that can analyze every image or solve every problem. Instead, researchers must manually re-annotate images or write new analysis software every time they want to ask new questions.

Machine learning (ML) offers a way to “automatically” find a customized image analysis algorithm for new research workflows. However, traditional supervised ML approaches (e.g., Artificial Neural Networks) require large datasets of pre-annotated images for training, which creates a circular problem: researchers must manually annotate their images in order to create a training dataset so that traditional ML approaches can find an algorithm to automatically annotate their images. This can be feasible for large, well-funded projects and domains (e.g., Medical Imaging, Self-Driving Cars) but not for smaller, exploratory projects where researchers want to use their data to test simple hypotheses or ask questions that have never been studied before. During this early stage of the scientific process, which we are calling “Exploratory Image Understanding,” it is common to manually annotate image and video frame-by-frame, which is an extremely slow process subject to variations in quality and detail.

### SEE-Insight Approach

The SEE-Insight Team is developing image understanding tools which focus on common workflows used in scientific image understanding for applications in engineering, medical imaging, biology, etc.  The goal is to develop tools that are more than just a manual annotation system. As the scientist annotates their images, the tools will take their annotations (starting from the very first image) and use machine learning to search the “algorithm space” to try and identify candidate algorithms based on their specified workflow. If a good candidate algorithm is found, then the tools will start making suggestions to the researcher. In the worst case, using just the tools will take no more time than scientists would need to annotate the images manually; the result will be an annotated dataset which they can use to conduct their science or to feed into a more traditional ML system. However, in the best case, a good candidate algorithm can be automatically identified, that can help speed up some, or all, of the annotation process, saving researcher time and speeding up their overall research workflow.

The SEE-Insight Project is researching and developing tools using the following design guidelines:

*	**_Transparent Interface Design:_** Transparent design was first outlined by Doug Norman in “Design of Everyday Things” and “The Invisible Computer.” In this context, a good interface is one where the computer becomes invisible and users can focus on what they are trying to do instead of how to do it using the computer. In the case of exploratory image understanding, transparent design allows the researcher to focus on analyzing the image rather than on the mechanics of the software.
*	**_Keeping the Researcher in the Loop:_** At every step in the analysis and annotation process, researchers can review the SEE tools  suggestions and accept, adjust or reject them as needed. The SEE tools always allows researchers to make the final decisions.
*	**_User Feedback and Confidence Measures:_** Providing feedback is key if the SEE tools is to gain and keep researchers’ trust. This feedback takes the form of measurements with confidence measures, which allows researchers to make an expert judgement about the likelihood of the suggested measurement being appropriate for the current question.
*	**_Feature Scaffolding:_** The SEE tools is designed to provide new users with more automation and step-by-step instructions, as well as additional functionality for “power users” who have gained familiarity and trust in the SEE tools.

# Summary video about SEE-Insight Research


<iframe width="560" height="315" src="https://www.youtube.com/embed/5inNPZ45Lsc" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>

# The SEE-Tools

- [SEE-Segment](https://see-insight.github.io/see-segment)

# Team 

- [List of current and previous team members](Contributors)

# Dirk's Research Guidelines 

- [Reviewing Scientific Articles](Article_Review)
- [Guidelines for Authorship in Scholarly Publications](Author_Guidelines)
- [Student Mentor-Mentee Agreement](Mentor_Agreement)
- [Dirk’s User Manual](User_Manual)
- [Dirk’s Guidelines for Project Code Repositories](Rules_for_Repos)

# Interested in joining?
Thank you for your interest in the SEE-Insight Lab. 

At the moment, **our lab does not have any funding available for new students**. However, there are several ways you can still stay connected and get involved:

### 1. Open Group Meetings
Our SEE‑Insight group meetings are open to the public, and visitors are always welcome. All of our work is open source, and some students have discovered meaningful ways to contribute simply by attending meetings, following ongoing discussions, and exploring active projects.

Dr. Colbry generally prefers to work with students who have some “skin in the game." For example, those earning course credit or being paid, because that allows him to provide clearer structure and expectations. However, a small number of highly motivated students have self‑identified interesting problems and contributed in substantial ways through our open‑source ecosystem.

If you’d like to join meetings, please email Dr. Colbry [colbrydi@msu.edu](mailto:colbrydi@msu.edu) and he can send you the room location, Zoom link, and/or add you to our group email list.

### 2. Opportunities Mailing List
Dr. Colbry maintains a list of students who are looking for research or job opportunities. When relevant opportunities are found, he forwards them to that list.

To join, please fill out [this form](https://forms.gle/feL3uTWVPi41Xh8SA)

### 3. Research for Credit Through VIP (Vertically Integrated Projects)
Some students in the SEE-Insight lab participate through the **Vertically Integrated Projects (VIP)** program, which allows them to earn **credit** while contributing to long‑term, multi-semester, faculty‑led research teams. VIP students build both technical depth and team‑based research experience over multiple semesters.

You can learn more about the msu VIP pilot [here](https://msu-cmse-courses.github.io/VIP_website/teams).

