pipeline {
  agent any
  stages {
    stage('workflow:sandbox') {
      when { anyOf { environment name: 'DATAGOV_WORKFLOW', value: 'sandbox' } }
      environment {
        ANSIBLE_VAULT_FILE = credentials('ansible-vault-secret')
        SSH_KEY_FILE = credentials('datagov-sandbox')
      }
      stages {
        stage('deploy:sandbox') {
          when { anyOf { branch 'fcs' } }
          steps {
            ansiColor('xterm') {
              echo 'Deploying with Ansible'
              copyArtifacts projectName: 'deploy-ci-platform-mb/develop', selector: lastSuccessful()
              sh 'mkdir deploy && tar xzf datagov-deploy.tar.gz -C deploy'
              dir('deploy') {
                sh 'bin/jenkins-deploy init'
                sh 'bin/jenkins-deploy ping sandbox inventory-next'
                sh 'bin/jenkins-deploy deploy sandbox inventory.yml --limit inventory-next'
              }
            }
          }
        }
      }
    }
    stage('workflow:production') {
      when { allOf {
          environment name: 'DATAGOV_WORKFLOW', value: 'production'
          branch 'fcs'
        }
      }
      environment {
        ANSIBLE_VAULT_FILE = credentials('ansible-vault-secret')
      }
      stages {
        stage('deploy:init') {
          steps {
            ansiColor('xterm') {
              copyArtifacts projectName: 'deploy-ci-platform-mb/master', selector: lastSuccessful()
              sh 'mkdir deploy && tar xzf datagov-deploy.tar.gz -C deploy'
              dir('deploy') {
                sh 'bin/jenkins-deploy init'
              }
            }
          }
        }
        stage('deploy:staging') {
          environment {
            SSH_KEY_FILE = credentials('datagov-prod-ssh')
          }
          steps {
            ansiColor('xterm') {
              dir('deploy') {
                sh 'bin/jenkins-deploy ping staging inventory-next'
                sh 'bin/jenkins-deploy deploy staging inventory.yml --limit inventory-next'
              }
            }
          }
        }
        stage('deploy:production') {
          environment {
            SSH_KEY_FILE = credentials('datagov-prod-ssh')
          }
          steps {
            ansiColor('xterm') {
              dir('deploy') {
                sh 'bin/jenkins-deploy ping production inventory-next'
                sh 'bin/jenkins-deploy deploy production inventory.yml --limit inventory-next'
              }
            }
          }
        }
      }
    }
  }
  post {
    always {
      step([$class: 'GitHubIssueNotifier', issueAppend: true, issueRepo: 'https://github.com/GSA/datagov-deploy.git'])
      cleanWs()
    }
  }
}
