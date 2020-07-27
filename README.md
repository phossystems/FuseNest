![2](https://user-images.githubusercontent.com/30301307/80922746-5edb1300-8d7f-11ea-8fee-337ab73c3d71.png)


# FuseNest
2D Nesting / Packing Add-In for Autodesk Fusion360 based on SVGNest

<img width="680" alt="Screenshot 2020-05-03 at 20 55 45" src="https://user-images.githubusercontent.com/30301307/80922930-9f875c00-8d80-11ea-84c1-dd7610ffb042.png">

# Features
* Nesting of bodies & components on rectangular sheets
* Spacing between parts
* Multiple sheets

# How to use
Launch the command and select the bodies you whish to nest. All bodies will be selected by default. We suggest having one body per component as this works the best, but having all bodies in the root component or a mix of both also works (but creates a lot of timeline objects). Bodies shouldn't overlap and should be placed further apart than the desired spacing.    
Set the parameters as required:

**Sheet Width/Height:**    
Width & Height of the rectangular sheet parts will be placed on.

**Sheet offset X/Y:**    
Distance between sheets    
e.g. X=-30mm Y=0mm will place the next sheet 30mm left of the previous one.

**Spacing:**    
Approximate spacing between parts. Set this a bit higher than your minimum spacing as it can vary by small amounts.

**Rotations:**    
The number of rotations the Algorithm will try. Setting this too high will drastically increase the time required to find a good solution, setting it too low will make it impossible to find some good solutions. Here are some suggested values:    
    
* Perfectly circular, square or Hexagonal parts: 2
* Good compromise between speed and quality: 4
* Odd/Organic shapes with high aspect ratio: 8+

<img width="1048" alt="Screenshot 2020-07-26 at 11 02 34" src="https://user-images.githubusercontent.com/30301307/88475385-86311e80-cf2f-11ea-81eb-339ca396b313.png">

Press "Start Nesting" to start the nesting process.    
This will open a new window and will start nesting after the selected bodies are loaded. This may take several minutes if the bodies are complex.    
The first round of nesting will take the longest. The Progress bar will indicate the approximate progress for the current iteration. After the first iteration, the algorithm will try to find better solutions in further iterations until it is stopped.    
    
Press "Apply Nest" to accept the current result or Press "Close" to go back to the previous step, deleting any progress done. Pressing "Stop Nest" will pause the process temporarily. It can be resumed by pressing "Start Nest"

<img width="1433" alt="Screenshot 2020-07-26 at 11 16 03" src="https://user-images.githubusercontent.com/30301307/88475564-6864b900-cf31-11ea-98ad-8cbc362105f1.png">

After pressing "Apply Nest" you will be back to the command. Press "OK" to confirm. Changing selected bodies or settings will void the previously calculated nesting data, so be careful.

# License
This free version is licensed under a **non-commercial** license intended for personal, educational & trial use. **A commercial license can be purchased from the Fusion360 App Store soon.** Please contact us if you need a different license, for example for reusing parts of this code commercially.

# Installation
**Installation through the Fusion360 App Store will be available soon**

* Download the Project as ZIP and extract it somewhere you can find again, but won't bother you. (or use git to clone it there)
* Open Fusion360 and press ADD-INS > Scripts and Add-ins
* Select the tab Add-Ins and click the green plus symbol next to "My Add-Ins"
* Navigate to the extracted Project folder and hit open
* The Add-in should now appear in the "My Add-Ins" list. Select it in the list. If desired check the "Run on Startup" checkbox and hit run.
* The Command will appear as Modify > 2D Nest

# Changelog

## 1.0 Initial Version
