pipeline {
    agent any
  
    environment {
        DOCKER_IMAGE = 'mohameds2/page'
        IMAGE_TAG = 'latest'
    }
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        stage('Build & Push Image') {
            steps {
                sh """
                docker compose up -d
                """
            }
        }
     
    post {
        success {
            echo '✅ Pipeline completed successfully!'
        }
        failure {
            echo '❌ Pipeline failed!'
        }
    }
}
