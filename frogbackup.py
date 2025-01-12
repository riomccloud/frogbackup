import getpass				# Hidden text inputs
import gettext				# Internationalization
import os					# Manage files
import subprocess			# Run shell commands
import sys					# System exit
import yaml					# Load the config file

# Check config.yaml file and load it
def initialChecks():
	# Try to load config.yaml file, stop if there's errors
	try:
		config = yaml.safe_load(open("config.yaml", "r", encoding="utf-8"))
	except FileNotFoundError:
		print("[ERROR] 'config.yaml' was not found. Check it and try again." "\n")
		input("Press Enter to exit...")
		sys.exit(1)
	except yaml.YAMLError as e:
		print(
			"[ERROR] 'config.yaml' is not formatted correctly:" "\n\n"
			f"{e}"
			"\n\n"
			"Check it and try again." "\n"
		)
		input(
			"Press Enter to exit..."
		)
		sys.exit(1)
	except Exception as e:
		print(
			"[ERROR] Unknown error:" "\n\n"
			f"{e}"
			"\n\n"
			"Check it and try again." "\n"
		)
		input("Press Enter to exit...")
		sys.exit(1)

	# Load the configured language from config.yaml
	try:
		configuredLanguage = (config.get("programSettings", []).get("language"))

		# Set the translations' directory
		languageDir = "locale"

		# If the configured language is English, fallback to the script's text
		if configuredLanguage == "en":
			translation = gettext.NullTranslations()
		# Else, load the translation files
		elif configuredLanguage == "pt_BR":
			translation = gettext.translation("frogbackup", localedir=languageDir, languages=[configuredLanguage])

		# Install GetText translation
		translation.install()
	except:
		# Set _ var here otherwise the script breaks in fallback mode
		global _
		_ = gettext.gettext
		print(
			"[WARNING] Language configured in 'config.yaml' is not supported or is not configured. Falling back to English." "\n"
		)

	# Create a list for possible missing/blank lines in config.yaml
	errors = []
	
	# Check for config.yaml integrity
	blockCounter = 0
	for backupEntryLine in config.get("backupLocations", []):
		blockCounter += 1
		if not backupEntryLine.get("name"):
			errors.append(f"name (block {blockCounter})")
		if not backupEntryLine.get("localPath"):
			errors.append(f"localPath (block {blockCounter})")
		if not backupEntryLine.get("remotePath"):
			errors.append(f"remotePath (block {blockCounter})")
		# Tip: other conditions check if the value is false, 0, empty; this one only checks for the line to exist, since 0 is a valid value
		if backupEntryLine.get("maxSnapshots") is None:
			errors.append(f"maxSnapshots (block {blockCounter})")
		if backupEntryLine.get("checkIntegrity") not in [0, 1, 2, 3]:
			errors.append(f"checkIntegrity (block {blockCounter})")
		# readDataSubset depends on checkIntegrity
		if not backupEntryLine.get("checkIntegrity") is None and not backupEntryLine.get("readDataSubset"):
			errors.append(f"readDataSubset (block {blockCounter})")
		if not backupEntryLine.get("groupBy"):
			errors.append(f"groupBy (block {blockCounter})")
	if errors:
		print(
			_("[ERROR] The following fields are blank or missing in 'config.yaml':") + f" {', '.join(errors)}." + "\n" +
			_("Check them and try again.")
		)
		sys.exit(1)

	# Returns the configured values to be used
	return config

# Start backing up files
def backupFiles(config):
	# Set backup counter to zero, to show progress
	backupCounter = 0

	# See how many backup entries the config.yaml file have, to show progress
	backupEntriesNumber = len(config.get("backupLocations", []))

	# Copy the enviroment variables of the system to a var, since we'll add a new var later
	enviromentVars = os.environ.copy()

	# For each backup entry on the config file
	for backupEntryLine in config.get("backupLocations", []):
		# Increase the backup counter
		backupCounter += 1

		while True:
			# Clear the screen content
			os.system("cls" if os.name == "nt" else "clear")

			# Print the configuration
			print(
				"==================================================" "\n\n"
				"FROGBACKUP v2.1 - " + _("Stage") + f" {backupCounter} " + _("of") + f" {backupEntriesNumber}" + "\n\n" +
				_("The utility will now backup") + f" '{backupEntryLine.get('name')}'." "\n" +
				_("If the data below is correct, you shall proceed.") + "\n\n" +
				_("LOCAL PATH:") + f" '{backupEntryLine.get('localPath')}'" "\n" +
				_("REMOTE PATH:") + f" '{backupEntryLine.get('remotePath')}'" "\n" +
				_("MAX SNAPSHOTS:") + f" {backupEntryLine.get('maxSnapshots')}" "\n" +
				_("CHECK INTEGRITY:") + f" {backupEntryLine.get('checkIntegrity')}" "\n" +
				_("READ DATA SUBSET:") + f" {backupEntryLine.get('readDataSubset')}" "\n" +
				_("GROUP BY:") + f" '{backupEntryLine.get('groupBy')}'")
			
			# If there are exclusions configured, display them
			if backupEntryLine.get("exclude"):
				exclude = backupEntryLine.get("exclude")
				print(_("EXCLUDE: ") + ", ".join(exclude))
			
			# If there are tags configured, display them
			if backupEntryLine.get("tags"):
				tags = backupEntryLine.get("tags")
				print(_("TAGS: ") + ", ".join(tags))
			
			# Finish printing the backup instance details
			print(
				"\n"
				"==================================================" "\n"
			)

			# Loop to keep the question if users' input is blank
			while True:
				# Ask for Restic's repository password
				passwordPrompt = _("Enter your Restic's repository password: ")
				enviromentVars["RESTIC_PASSWORD"] = getpass.getpass(passwordPrompt)

				# Check if user typed a valid password
				if not enviromentVars["RESTIC_PASSWORD"]:
					print(
						"\n" +
						_("Please enter your password to continue. Blank inputs are invalid.")
					)
				else:
					break

			# Clear the screen content
			os.system("cls" if os.name == "nt" else "clear")
			
			# Check repository's integrity as configured in the settings file
			print(
				_("STEP 1: Checking repository's integrity...") + "\n"
				"==================================================" "\n"
			)
			
			# Check if repository's integrity check is enabled
			if backupEntryLine.get("checkIntegrity") != 0:
				# Sets the Restic command to check integrity
				checkRepositoryIntegrityCommand = [
					"restic",
					"-r", backupEntryLine.get("remotePath")
				]
				
				# Select the correct command based in the settings file
				if backupEntryLine.get("checkIntegrity") == 1:
					checkRepositoryIntegrityCommand.append("check")
				elif backupEntryLine.get("checkIntegrity") == 2:
					checkRepositoryIntegrityCommand.extend([
						"check",
						"--read-data"
					])
				elif backupEntryLine.get("checkIntegrity") == 3:
					checkRepositoryIntegrityCommand.extend([
						"check",
						"--read-data-subset",
						str(backupEntryLine.get("readDataSubset"))
					])

				# Run command to check for repository's integrity and get its output
				checkRepositoryIntegrityOutput = subprocess.Popen(
					checkRepositoryIntegrityCommand,
					encoding="UTF-8",
					env=enviromentVars,
					stderr=subprocess.PIPE,
					stdout=None
				)

				# Wait for the command to finish
				checkRepositoryIntegrityOutput.wait()

				# If there were errors, display them
				checkRepositoryIntegrityOutputErrors = checkRepositoryIntegrityOutput.stderr.read()
				if checkRepositoryIntegrityOutputErrors:
					print(checkRepositoryIntegrityOutputErrors)

				# Check if password is wrong, if true warns user and return to the beginning of the loop
				if "wrong password" in checkRepositoryIntegrityOutputErrors:
					print(_("[ERROR] The password you entered is incorrect.") + "\n")
					input(_("Press Enter to restart this backup stage..."))
					continue

				# Finish the integrity check process
				print(
					"\n" +
					_("INTEGRITY CHECK FINISHED!") + "\n"
					"==================================================" "\n\n" +
					_("Please confirm if the repository is healthy reading the output above.")
				)

				# Loop to keep the question if users' input is invalid
				while True:
					# Ask if integrity is Ok
					isIntegrityOk = input(_("Is the repository healthy (Y/N)? ")).strip().lower()

					# Yes and No, other letters represent these two words in different languages
					if isIntegrityOk in ["y", "s", "n"]:
						break
					else:
						print(
							"\n" +
							_("Invalid input. Please type Y (Yes) or N (No).")
						)
				
				# If integrity is not Ok, warn the user
				if not isIntegrityOk in ["y", "s"]:
					print(
						"\n" +
						_("Well, that's no good. =(") + "\n" +
						_("Check Restic's docs to proceed in trying to repair this repository.") + "\n" +
						_("FrogBackup will close. If you need help, contact your system's administrator.") + "\n" +
						_('As a wise penguin once said: "Bailing out, you are on your own. Good luck."') + "\n"
					)
					
					# Exit with error code
					input(_("Press Enter to exit..."))
					sys.exit(1)
			else:
				print(_("[INFO] Skiping this step since the repository is configured to not check its integrity."))

			# Delete old snapshots as configured in the settings file
			print(
				"\n" +
				_("STEP 2: Keeping the last") + f" {backupEntryLine.get('maxSnapshots')} " + _("snapshots, deleting the rest...") + "\n"
				"==================================================" "\n"
			)

			# Delete old snapshots if configured to do so
			if backupEntryLine.get("maxSnapshots") > 0:
				# Run the Restic command to purge old snapshots
				deleteOldSnapshotsCommand = [
					"restic",
					"-r", backupEntryLine.get("remotePath"),
					"forget",
					"--keep-last", str(backupEntryLine.get("maxSnapshots")),
					"--prune"
				]
				
				# If groupBy is configured, extend it (append doesn't work)
				if backupEntryLine.get("groupBy") and backupEntryLine.get("groupBy") != "default":
					deleteOldSnapshotsCommand.extend(["--group-by", str(backupEntryLine.get("groupBy"))])
				
				# Run the command
				deleteOldSnapshotsOutput = subprocess.Popen(
					deleteOldSnapshotsCommand,
					encoding="UTF-8",
					env=enviromentVars,
					stderr=None,
					stdout=None
				)

				# Wait for the command to finish
				deleteOldSnapshotsOutput.wait()
			# If not configured, inform the user that this step will be skiped
			else:
				print(_("[INFO] Skiping this step since the repository is not configured to delete old snapshots."))

			# Backup files
			print(
				"\n" +
				_("STEP 3: Backing up files to the remote path...") + "\n"
				"==================================================" "\n"
			)
			
			# Set the command
			backupCommand = [
				"restic",
				"-r", backupEntryLine.get("remotePath"),
				"backup", ".",
				"--skip-if-unchanged"
			]

			# If tags are configured, append them
			if backupEntryLine.get("tags"):
				for tagEntry in backupEntryLine.get("tags"):
					backupCommand.append("--tag")
					backupCommand.append(tagEntry)
			
			# If exclusions are configured, append them
			if backupEntryLine.get("exclude"):
				for excludeEntry in backupEntryLine.get("exclude"):
					backupCommand.append("--exclude")
					backupCommand.append(excludeEntry)
			
			# Run the Restic command to backup files
			backupOutput = subprocess.Popen(
				backupCommand,
				cwd=backupEntryLine.get("localPath"),
				encoding="UTF-8",
				env=enviromentVars,
				stderr=None,
				stdout=None
			)

			# Wait for the command to finish
			backupOutput.wait()

			# Show differences between snapshots
			print(
				"\n" +
				_("STEP 4: Listing differences between the two latest snapshots...") + "\n"
				"==================================================" "\n"
			)

			# Run the Restic command that lists snapshots
			listSnapshotsCommand = [
				"restic",
				"-r", backupEntryLine.get("remotePath"),
				"snapshots"
			]
			
			# If groupBy variable is configured, append it to the command
			if backupEntryLine.get("groupBy") and backupEntryLine.get("groupBy") != "default":
				listSnapshotsCommand.extend(["--group-by", str(backupEntryLine.get("groupBy"))])
			
			# Run the command
			listSnapshotsOutput = subprocess.run(
				listSnapshotsCommand,
				capture_output=True,
				encoding="UTF-8",
				env=enviromentVars,
				text=True
			)

			# Separate the output of the command in lines, reversed
			dividedOutput = list(reversed(listSnapshotsOutput.stdout.splitlines()))

			# Check if the repository has only one snapshot - if true, don't compare snapshots
			if not any(char.isdigit() for char in dividedOutput[3]):
				print(_("[INFO] The repository contains a single snapshot. Therefore, the utility will not try to compare snapshots."))
			else:
				# Get the IDs of the two latest snapshots
				latestSnapshotID, penultimateSnapshotID = dividedOutput[2][:8], dividedOutput[3][:8]

				# Display differences between the two last snapshots
				lastSnapshotsDiffCommand = [
					"restic",
					"-r", backupEntryLine.get("remotePath"),
					"diff",
					penultimateSnapshotID,
					latestSnapshotID
				]

				lastSnapshotsDiffOutput = subprocess.Popen(
					lastSnapshotsDiffCommand,
					encoding="UTF-8",
					env=enviromentVars,
					stderr=None,
					stdout=None
				)
				
				# Wait for the command to finish
				lastSnapshotsDiffOutput.wait()
			
			# Finish the backup process
			print(
				"\n" +
				_("BACKUP FINISHED!") + "\n"
				"==================================================" "\n\n" +
				_("Please confirm if the entire process ran correctly reading the output above.")
			)

			# Loop to keep the question if users' input is invalid
			while True:
				# Ask if backup was successful
				isBackupSuccessful = input(_("Was the backup successful (Y/N)? ")).strip().lower()

				# Yes and No, other letters represent these two words in different languages
				if isBackupSuccessful in ["y", "s", "n"]:
					break
				else:
					print(
						"\n" +
						_("Invalid input. Please type Y (Yes) or N (No).")
					)
			
			# If backup ran correctly, continue to the next one
			if isBackupSuccessful in ["y", "s"]:
				break
			else:
				print(
					"\n" +
					_("Ok, take your time to fix what needs to be fixed.") + "\n" +
					_("When done, continue following the questions below.") + "\n"
				)

				# Loop to keep the question if users' input is invalid
				while True:
					# Ask if user wants to delete latest snapshot
					# Useful if Restic was able to create one, but something went wrong (example: data rot noticed on snapshot differences)
					doDeleteLatestSnapshot = input(
						_("CAUTION: Do you want to delete the latest snapshot (Y/N)?") + "\n" +
						_("This is useful only if Restic was able to create one in step 3. ")
					).strip().lower()

					# Check for invalid input
					if doDeleteLatestSnapshot in ["y", "s", "n"]:
						break
					else:
						print(
							"\n" +
							_("Invalid input. Please type Y (Yes) or N (No).")
						)
				
				# If user wants to delete the latest snapshot, do it
				if doDeleteLatestSnapshot in ["y", "s"]:
					# Delete latest snapshot
					print(
						"\n" +
						_("EXTRA STEP: Deleting the latest snapshot...") + "\n"
						"==================================================" "\n"
					)

					# Run the command to delete the latest snapshot
					deleteLatestSnapshotCommand = [
						"restic",
						"-r", backupEntryLine.get("remotePath"),
						"forget", "latest",
						"--prune"
					]

					# Get its output
					deleteLatestSnapshotOutput = subprocess.Popen(
						deleteLatestSnapshotCommand,
						encoding="UTF-8",
						env=enviromentVars,
						stderr=None,
						stdout=None
					)

					# Wait to the program to finish
					deleteLatestSnapshotOutput.wait()

					print(
						"\n" +
						_("LATEST SNAPSHOT DELETED!") + "\n"
						"==================================================" "\n\n" +
						_("Read the output above to confirm that the changes were successful.") + "\n"
					)
					input(_("Press Enter to restart this backup stage..."))

def main():
	# Check config.yaml file and load it
	config = initialChecks()

	# Change window title
	programTitle = "FrogBackup v2.1"
	if os.name == "nt":
		os.system(f"title {programTitle}")
	else:
		sys.stdout.write(f"\033]0;{programTitle}\007")
		sys.stdout.flush()

	# Initial screen
	print(
		"==================================================" "\n\n"
		"FROGBACKUP v2.1" "\n\n" +
		_("Welcome to FrogBackup! The utility has loaded, passed\nthe initial checks and is ready to start.") + "\n\n"
		"==================================================" "\n"
	)
	input(_("Press Enter to continue..."))
	
	# Call the backup def
	backupFiles(config)

	# Clear the screen content
	os.system("cls" if os.name == "nt" else "clear")

	print(
		"==================================================" "\n\n"
		"FROGBACKUP v2.1" "\n\n" +
		_("The utility is now exiting. Thanks for using FrogBackup!") + "\n\n"
		"==================================================" "\n"
	)

	input(_("Press Enter to exit..."))

if __name__ == "__main__":
	main()