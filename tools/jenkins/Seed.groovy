job("Iris-Seed") {
	description("Seed DSL job to create/update Iris jobs")
	keepDependencies(false)
	scm {
		git {
			remote {
				github("iheartradio/iris", "ssh")
				credentials("ihr-deployer")
			}
			branch("master")
		}
	}
	disabled(false)
	triggers {
		scm("H/5 * * * *") {
			ignorePostCommitHooks(false)
		}
	}
	concurrentBuild(false)
        configure {
                it / 'properties' / 'jenkins.model.BuildDiscarderProperty' {
                        strategy {
                                'daysToKeep'('-1')
                                'numToKeep'('10')
                                'artifactDaysToKeep'('-1')
                                'artifactNumToKeep'('-1')
                        }
                }
        }
	steps {
		dsl {
			external('tools/jenkins/Seed.groovy')
			ignoreExisting(false)
			removeAction("IGNORE")
			removeViewAction("IGNORE")
			lookupStrategy("JENKINS_ROOT")
		}
	}
}

job("Iris-Deploy") {
	description("Deploys Iris Updates")
	keepDependencies(false)
	scm {
		git {
			remote {
				github("iheartradio/iris", "ssh")
				credentials("ihr-deployer")
			}
			branch("master")
		}
	}
	disabled(false)
	triggers {
		githubPush()
		scm("H/5 * * * *") {
			ignorePostCommitHooks(false)
		}
	}
	concurrentBuild(false)
	steps {
		shell("""# DO NOT EDIT - Managed via DSL

# Make sure venv and dist directories are removed
rm -fR \$WORKSPACE/venv \$WORKSPACE/dist

# CD into workspace directory
cd \$WORKSPACE

# Run pyinstaller to create Iris package
virtualenv venv --python=python3.5
. venv/bin/activate
pip install -r requirements.txt
pip install --no-use-pep517 pyinstaller==3.4

# Update build info so Iris is aware of its own version, etc.
sed -i -e"s/^IRIS_VERSION.*/IRIS_VERSION = 0.\$BUILD_NUMBER/" -e"s/^IRIS_REVISION.*/IRIS_REVISION = \$GIT_COMMIT/" -e"s/^IRIS_PYTHON_VERSION.*/IRIS_PYTHON_VERSION = \$(python --version 2>&1 | cut -f2 -d' ')/" -e"s/^IRIS_BUILD_DATE.*/IRIS_BUILD_DATE = \$(date +%F_%T)/" \$WORKSPACE/iris/run.py

# Build
pyinstaller --paths=venv/lib/python3.5/site-packages/ --add-data=iris.cfg:. --clean main.py

# Set AWS CLI variables
export AWS_ACCESS_KEY_ID=\$IRIS_S3_KEY_ID
export AWS_SECRET_ACCESS_KEY=\$IRIS_S3_KEY_SECRET

cd dist

# Package Iris into a tarball
/bin/tar czvf ../iris.tar.gz main

cd \$WORKSPACE

# Generate version data
echo "Generated on: \$(date)" > version.txt
echo "Build number: \$BUILD_NUMBER" >> version.txt
echo "Git branch: \$GIT_BRANCH" >> version.txt
echo "Git commit: \$GIT_COMMIT" >> version.txt

# List contents of Iris S3 bucket
/usr/local/bin/aws s3 ls ihr-iris

# Push Iris build to S3
/usr/local/bin/aws s3 cp iris.tar.gz s3://ihr-iris/dist/
/usr/local/bin/aws s3 cp version.txt s3://ihr-iris/dist/""")
	}
	wrappers {
		credentialsBinding {
			string("IRIS_S3_KEY_ID", "IRIS_S3_KEY_ID")
			string("IRIS_S3_KEY_SECRET", "IRIS_S3_KEY_SECRET")
		}
	}
	configure {
		it / 'properties' / 'jenkins.model.BuildDiscarderProperty' {
			strategy {
				'daysToKeep'('-1')
				'numToKeep'('10')
				'artifactDaysToKeep'('-1')
				'artifactNumToKeep'('-1')
			}
		}
	}
	properties {
		githubProjectUrl('https://github.com/git@github.com:iheartradio/iris.git/')
	}
	publishers {
		slackNotifier {
			room('iris')
			notifyAborted(true)
			notifyFailure(true)
			notifyNotBuilt(true)
			notifyUnstable(true)
			notifyBackToNormal(true)
			notifySuccess(true)
			notifyRepeatedFailure(true)
			startNotification(true)
			includeTestSummary(false)
			includeCustomMessage(false)
			customMessage(null)
			baseUrl('https://ihm-software.slack.com/services/hooks/jenkins-ci/')
			sendAs(null)
			commitInfoChoice('AUTHORS')
			tokenCredentialId('slack-iris')
		}
	}
}

listView("Iris") {
	jobs {
		name("Iris-Deploy")
		name("Iris-Seed")
	}
	columns {
		status()
		weather()
		name()
		lastSuccess()
		lastFailure()
		lastDuration()
		buildButton()
	}
}
