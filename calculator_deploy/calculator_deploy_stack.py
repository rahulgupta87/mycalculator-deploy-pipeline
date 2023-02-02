from aws_cdk import (
    # Duration,
    Stack,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as codepipeline_actions,
    aws_codebuild as codebuild,
    aws_secretsmanager as secretsmanager
    
)
from constructs import Construct

import aws_cdk

class CalculatorDeployStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        gitHubToken = secretsmanager.Secret.from_secret_attributes(self, "GitHubToken",
            secret_complete_arn="arn:aws:secretsmanager:us-east-1:721251530782:secret:gitSecretDetails-u2GwRs",
        )

        pipeline = codepipeline.Pipeline(self, "calculatorAppCodePipeline",pipeline_name="calculatorAppCodePipeline")

        source_output = codepipeline.Artifact()
        source_action = codepipeline_actions.GitHubSourceAction(
            action_name="SourceAction",
            owner="rahulgupta87",
            repo="mycalculator",
            oauth_token=aws_cdk.SecretValue.secrets_manager("gitSecretDetails"),
            branch="main",
            output=source_output
        )
        source_stage = pipeline.add_stage(stage_name="Source")
        source_stage.add_action(source_action)

        approval_action = codepipeline_actions.ManualApprovalAction(
            action_name="ApprovalAction"
        )
        approval_stage = pipeline.add_stage(stage_name="Approval")
        approval_stage.add_action(approval_action)

        env_variables = {
            "ENVEKS_CLUSTER_NAME_VAR_1": "value_1"
        }

        projectBuild = codebuild.PipelineProject(
            self, "calculatorAppBuildProject",
            project_name = "calculatorAppBuildProject",
            build_spec=codebuild.BuildSpec.from_object({
                'version': '0.2',
                'phases': {
                    'install': {
                        'commands': [
                            'pip3 install -r requirements.txt'
                        ]
                    },
                    'build': {
                        'commands': [
                            'echo "Building application image..."',
                            'docker build -t calculator .',
                            'echo "Uploading the image to the repository..."',
                            'docker tag calculator rgupta87/mycalculator:latest',
                            'docker push rgupta87/mycalculator:latest',
                            'echo "Logging in to the EKS cluster..."',
                            'aws eks --region $AWS_DEFAULT_REGION update-kubeconfig --name $EKS_CLUSTER_NAME',
                            'echo "Deploying the application to EKS..."',
                            'kubectl apply -f deployment_aws.yaml',
                            'echo "Waiting for the deployment to complete..."',
                            'kubectl rollout status deployment/calculator',
                            'echo "Application deployed successfully!"'
                        ]
                    }
                }
            }),
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_5_0,
                environment_variables=env_variables,
                privileged=True
            )
        )

        build_action = codepipeline_actions.CodeBuildAction(
            action_name="BuildDeployAction",
            project=projectBuild,
            input=source_output
        )

        build_stage = pipeline.add_stage(stage_name="Build&Deploy")
        build_stage.add_action(build_action)