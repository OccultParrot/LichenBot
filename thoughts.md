# My Thoughts

So far, this is the requested functionality:
- [ ] Injury / infection roller for bone breaks

----

## Injury / Infection Roller for Bone Breaks

When someone gets bone broken in the game, 
they can choose to use this command to see if they get an infection or permanent wound of some sort.

General ideas for how this will work:
- Read from JSON file for the possible injuries and infections, and their associated probabilities
- Roll a random number to determine if the injury or infection occurs, and which one it is
- Output the result to the user, including any pertinent information regarding the affliction. 
Maybe include an array of details for each affliction?
- If possible, make a wheel of fortune style spinner to visually represent the probabilities of each outcome.
I saw a way to do this via images attached to the message. Research it.
- Include a command to list all possible injuries and infections, along with their probabilities and details. 
- This could be useful for players to understand the risks before they decide to use the roller.
- Possibly Track the player's history of afflictions, 
on a per-character basis, 
so they can see what they've been through and maybe even have some sort of cumulative effect if they get multiple afflictions over time.

Tasks:
- [ ] Create JSON file with possible injuries and infections, their probabilities, and details.
Include a schema so it's easy to add new afflictions in the future.
- [x] Load from JSON file when the bot starts up.
- [ ] Implement the roller command to determine if an affliction occurs and which one it is.
- [ ] Implement the command to list all possible afflictions with their probabilities and details.
- [ ] Set up storage of player history of afflictions, and implement the command to view this history. DB? JSON file?
- [ ] Implement the command for viewing history of afflictions for a character.
