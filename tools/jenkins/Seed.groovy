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
			external('dsl/src/Seed.groovy')
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
		shell("echo Placeholder")
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
