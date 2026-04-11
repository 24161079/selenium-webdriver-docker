output "web_app_url" {
  description = "URL to access the Flask web application"
  value       = "http://${aws_eip.selenium.public_ip}:5000"
}

output "instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.selenium.id
}

output "instance_public_ip" {
  description = "Public IP address of the EC2 instance"
  value       = aws_eip.selenium.public_ip
}

output "instance_private_ip" {
  description = "Private IP address of the EC2 instance"
  value       = aws_instance.selenium.private_ip
}

output "security_group_id" {
  description = "Security group ID"
  value       = aws_security_group.selenium.id
}

output "selenium_grid_url" {
  description = "Selenium Grid URL (Selenium Hub)"
  value       = "http://${aws_eip.selenium.public_ip}:4444"
}

output "novnc_url" {
  description = "noVNC viewer URL to watch tests running"
  value       = "http://${aws_eip.selenium.public_ip}:7901/"
}

output "ssh_command" {
  description = "SSH command to connect to the instance"
  value       = "ssh -i <your-key.pem> ubuntu@${aws_eip.selenium.public_ip}"
}

output "s3_bucket_name" {
  description = "S3 bucket used for downloaded templates"
  value       = aws_s3_bucket.templates.bucket
}

output "s3_key_prefix" {
  description = "S3 object prefix used for downloaded templates"
  value       = var.s3_key_prefix
}

output "docker_compose_logs_command" {
  description = "Command to view Docker Compose logs"
  value       = "ssh -i <your-key.pem> ubuntu@${aws_eip.selenium.public_ip} 'cd /app && docker compose logs -f'"
}
