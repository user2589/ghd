SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;
SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='TRADITIONAL,ALLOW_INVALID_DATES';
SET @OLD_TIME_ZONE=@@session.time_zone;

-- -----------------------------------------------------
-- Table `users`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `users` ;

CREATE TABLE IF NOT EXISTS `users` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `login` VARCHAR(40) NOT NULL,
  `company` VARCHAR(255) NULL DEFAULT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `type` VARCHAR(255) NOT NULL DEFAULT 'USR',
  `fake` TINYINT(1) NOT NULL DEFAULT '0',
  `deleted` TINYINT(1) NOT NULL DEFAULT '0',
  `long` DECIMAL(11,8),
  `lat` DECIMAL(10,8),
  `country_code` CHAR(3),
  `state` VARCHAR(255),
  `city` VARCHAR(255),
  `location` VARCHAR(255) NULL DEFAULT NULL,
  PRIMARY KEY (`id`) )
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8;

-- -----------------------------------------------------
-- Table `projects`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `projects` ;

SET time_zone='+0:00';
CREATE TABLE IF NOT EXISTS `projects` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `url` VARCHAR(141) NULL DEFAULT NULL,
  `owner_id` INT(11) NULL DEFAULT NULL,
  `name` VARCHAR(255) NOT NULL,
  `description` VARCHAR(255) NULL DEFAULT NULL,
  `language` VARCHAR(255) NULL DEFAULT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `forked_from_id` INT(11) NULL DEFAULT NULL,
  `deleted` TINYINT(1) NOT NULL DEFAULT '0',
  `updated_at` TIMESTAMP NOT NULL DEFAULT '1970-01-01 00:00:01',
  PRIMARY KEY (`id`) ,
  CONSTRAINT `projects_ibfk_1`
    FOREIGN KEY (`owner_id`)
    REFERENCES `users` (`id`),
  CONSTRAINT `projects_ibfk_2`
    FOREIGN KEY (`forked_from_id`)
    REFERENCES `projects` (`id`))
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8;
SET time_zone=@OLD_TIME_ZONE;

-- -----------------------------------------------------
-- Table `commits`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `commits` ;

CREATE TABLE IF NOT EXISTS `commits` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `sha` CHAR(40) NOT NULL,
  `author_id` INT(11) NULL DEFAULT NULL,
  `committer_id` INT(11) NULL DEFAULT NULL,
  `project_id` INT(11) NULL DEFAULT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) ,
  CONSTRAINT `commits_ibfk_1`
    FOREIGN KEY (`author_id`)
    REFERENCES `users` (`id`),
  CONSTRAINT `commits_ibfk_2`
    FOREIGN KEY (`committer_id`)
    REFERENCES `users` (`id`),
  CONSTRAINT `commits_ibfk_3`
    FOREIGN KEY (`project_id`)
    REFERENCES `projects` (`id`))
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8;

-- -----------------------------------------------------
-- Table `commit_comments`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `commit_comments` ;

CREATE TABLE IF NOT EXISTS `commit_comments` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `commit_id` INT(11) NOT NULL,
  `user_id` INT(11) NOT NULL,
  `body` VARCHAR(256) NULL DEFAULT NULL,
  `line` INT(11) NULL DEFAULT NULL,
  `position` INT(11) NULL DEFAULT NULL,
  `comment_id` INT(11) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) ,
  CONSTRAINT `commit_comments_ibfk_1`
    FOREIGN KEY (`commit_id`)
    REFERENCES `commits` (`id`),
  CONSTRAINT `commit_comments_ibfk_2`
    FOREIGN KEY (`user_id`)
    REFERENCES `users` (`id`))
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8;

-- -----------------------------------------------------
-- Table `commit_parents`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `commit_parents` ;

CREATE TABLE IF NOT EXISTS `commit_parents` (
  `commit_id` INT(11) NOT NULL,
  `parent_id` INT(11) NOT NULL,
  CONSTRAINT `commit_parents_ibfk_1`
    FOREIGN KEY (`commit_id`)
    REFERENCES `commits` (`id`),
  CONSTRAINT `commit_parents_ibfk_2`
    FOREIGN KEY (`parent_id`)
    REFERENCES `commits` (`id`))
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8;

-- -----------------------------------------------------
-- Table `followers`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `followers` ;

CREATE TABLE IF NOT EXISTS `followers` (
  `follower_id` INT(11) NOT NULL,
  `user_id` INT(11) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`follower_id`, `user_id`) ,
  CONSTRAINT `follower_fk1`
    FOREIGN KEY (`follower_id`)
    REFERENCES `users` (`id`),
  CONSTRAINT `follower_fk2`
    FOREIGN KEY (`user_id`)
    REFERENCES `users` (`id`))
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8;

-- -----------------------------------------------------
-- Table `pull_requests`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `pull_requests` ;

CREATE TABLE IF NOT EXISTS `pull_requests` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `head_repo_id` INT(11) NULL DEFAULT NULL,
  `base_repo_id` INT(11) NOT NULL,
  `head_commit_id` INT(11) NULL DEFAULT NULL,
  `base_commit_id` INT(11) NOT NULL,
  `pullreq_id` INT(11) NOT NULL,
  `intra_branch` TINYINT(1) NOT NULL,
  PRIMARY KEY (`id`) ,
  CONSTRAINT `pull_requests_ibfk_1`
    FOREIGN KEY (`head_repo_id`)
    REFERENCES `projects` (`id`),
  CONSTRAINT `pull_requests_ibfk_2`
    FOREIGN KEY (`base_repo_id`)
    REFERENCES `projects` (`id`),
  CONSTRAINT `pull_requests_ibfk_3`
    FOREIGN KEY (`head_commit_id`)
    REFERENCES `commits` (`id`),
  CONSTRAINT `pull_requests_ibfk_4`
    FOREIGN KEY (`base_commit_id`)
    REFERENCES `commits` (`id`))
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8;

-- -----------------------------------------------------
-- Table `issues`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `issues` ;

CREATE TABLE IF NOT EXISTS `issues` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `repo_id` INT(11) NULL DEFAULT NULL,
  `reporter_id` INT(11) NULL DEFAULT NULL,
  `assignee_id` INT(11) NULL DEFAULT NULL,
  `pull_request` TINYINT(1) NOT NULL,
  `pull_request_id` INT(11) NULL DEFAULT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `issue_id` INT(11) NOT NULL,
  PRIMARY KEY (`id`) ,
  CONSTRAINT `issues_ibfk_1`
    FOREIGN KEY (`repo_id`)
    REFERENCES `projects` (`id`),
  CONSTRAINT `issues_ibfk_2`
    FOREIGN KEY (`reporter_id`)
    REFERENCES `users` (`id`),
  CONSTRAINT `issues_ibfk_3`
    FOREIGN KEY (`assignee_id`)
    REFERENCES `users` (`id`),
  CONSTRAINT `issues_ibfk_4`
    FOREIGN KEY (`pull_request_id`)
    REFERENCES `pull_requests` (`id`))
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8;

-- -----------------------------------------------------
-- Table `issue_comments`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `issue_comments` ;

CREATE TABLE IF NOT EXISTS `issue_comments` (
  `issue_id` INT(11) NOT NULL,
  `user_id` INT(11) NOT NULL,
  `comment_id` MEDIUMTEXT NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT `issue_comments_ibfk_1`
    FOREIGN KEY (`issue_id`)
    REFERENCES `issues` (`id`),
  CONSTRAINT `issue_comments_ibfk_2`
    FOREIGN KEY (`user_id`)
    REFERENCES `users` (`id`))
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8;

-- -----------------------------------------------------
-- Table `issue_events`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `issue_events` ;

CREATE TABLE IF NOT EXISTS `issue_events` (
  `event_id` MEDIUMTEXT NOT NULL,
  `issue_id` INT(11) NOT NULL,
  `actor_id` INT(11) NOT NULL,
  `action` VARCHAR(255) NOT NULL,
  `action_specific` VARCHAR(50) NULL DEFAULT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT `issue_events_ibfk_1`
    FOREIGN KEY (`issue_id`)
    REFERENCES `issues` (`id`),
  CONSTRAINT `issue_events_ibfk_2`
    FOREIGN KEY (`actor_id`)
    REFERENCES `users` (`id`))
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8;

-- -----------------------------------------------------
-- Table `repo_labels`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `repo_labels` ;

CREATE TABLE IF NOT EXISTS `repo_labels` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `repo_id` INT(11) NULL DEFAULT NULL,
  `name` VARCHAR(24) NOT NULL,
  PRIMARY KEY (`id`) ,
  CONSTRAINT `repo_labels_ibfk_1`
    FOREIGN KEY (`repo_id`)
    REFERENCES `projects` (`id`))
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8;

-- -----------------------------------------------------
-- Table `issue_labels`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `issue_labels` ;

CREATE TABLE IF NOT EXISTS `issue_labels` (
  `label_id` INT(11) NOT NULL,
  `issue_id` INT(11) NOT NULL,
  PRIMARY KEY (`issue_id`, `label_id`) ,
  CONSTRAINT `issue_labels_ibfk_1`
    FOREIGN KEY (`label_id`)
    REFERENCES `repo_labels` (`id`),
  CONSTRAINT `issue_labels_ibfk_2`
    FOREIGN KEY (`issue_id`)
    REFERENCES `issues` (`id`))
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8;

-- -----------------------------------------------------
-- Table `organization_members`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `organization_members` ;

CREATE TABLE IF NOT EXISTS `organization_members` (
  `org_id` INT(11) NOT NULL,
  `user_id` INT(11) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`org_id`, `user_id`) ,
  CONSTRAINT `organization_members_ibfk_1`
    FOREIGN KEY (`org_id`)
    REFERENCES `users` (`id`),
  CONSTRAINT `organization_members_ibfk_2`
    FOREIGN KEY (`user_id`)
    REFERENCES `users` (`id`))
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8;

-- -----------------------------------------------------
-- Table `project_commits`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `project_commits` ;

CREATE TABLE IF NOT EXISTS `project_commits` (
  `project_id` INT(11) NOT NULL DEFAULT '0',
  `commit_id` INT(11) NOT NULL DEFAULT '0',
  CONSTRAINT `project_commits_ibfk_1`
    FOREIGN KEY (`project_id`)
    REFERENCES `projects` (`id`),
  CONSTRAINT `project_commits_ibfk_2`
    FOREIGN KEY (`commit_id`)
    REFERENCES `commits` (`id`))
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8;

-- -----------------------------------------------------
-- Table `project_members`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `project_members` ;

CREATE TABLE IF NOT EXISTS `project_members` (
  `repo_id` INT(11) NOT NULL,
  `user_id` INT(11) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `ext_ref_id` VARCHAR(24) NOT NULL DEFAULT '0',
  PRIMARY KEY (`repo_id`, `user_id`) ,
  CONSTRAINT `project_members_ibfk_1`
    FOREIGN KEY (`repo_id`)
    REFERENCES `projects` (`id`),
  CONSTRAINT `project_members_ibfk_2`
    FOREIGN KEY (`user_id`)
    REFERENCES `users` (`id`))
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8;

-- -----------------------------------------------------
-- Table `project_languages`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `project_languages` ;

CREATE TABLE IF NOT EXISTS `project_languages` (
  `project_id` INT(11) NOT NULL,
  `language` VARCHAR(255) NULL DEFAULT NULL,
  `bytes` INT(11),
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT `project_languages_ibfk_1`
    FOREIGN KEY (`project_id`)
    REFERENCES `projects` (`id`))
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8;

-- -----------------------------------------------------
-- Table `pull_request_comments`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `pull_request_comments` ;

CREATE TABLE IF NOT EXISTS `pull_request_comments` (
  `pull_request_id` INT(11) NOT NULL,
  `user_id` INT(11) NOT NULL,
  `comment_id` MEDIUMTEXT NOT NULL,
  `position` INT(11) NULL DEFAULT NULL,
  `body` VARCHAR(256) NULL DEFAULT NULL,
  `commit_id` INT(11) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT `pull_request_comments_ibfk_1`
    FOREIGN KEY (`pull_request_id`)
    REFERENCES `pull_requests` (`id`),
  CONSTRAINT `pull_request_comments_ibfk_2`
    FOREIGN KEY (`user_id`)
    REFERENCES `users` (`id`),
  CONSTRAINT `pull_request_comments_ibfk_3`
    FOREIGN KEY (`commit_id`)
    REFERENCES `commits` (`id`))
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8;

-- -----------------------------------------------------
-- Table `pull_request_commits`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `pull_request_commits` ;

CREATE TABLE IF NOT EXISTS `pull_request_commits` (
  `pull_request_id` INT(11) NOT NULL,
  `commit_id` INT(11) NOT NULL,
  PRIMARY KEY (`pull_request_id`, `commit_id`) ,
  CONSTRAINT `pull_request_commits_ibfk_1`
    FOREIGN KEY (`pull_request_id`)
    REFERENCES `pull_requests` (`id`),
  CONSTRAINT `pull_request_commits_ibfk_2`
    FOREIGN KEY (`commit_id`)
    REFERENCES `commits` (`id`))
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8;

-- -----------------------------------------------------
-- Table `pull_request_history`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `pull_request_history` ;

CREATE TABLE IF NOT EXISTS `pull_request_history` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `pull_request_id` INT(11) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `action` VARCHAR(255) NOT NULL,
  `actor_id` INT(11) NULL DEFAULT NULL,
  PRIMARY KEY (`id`) ,
  CONSTRAINT `pull_request_history_ibfk_1`
    FOREIGN KEY (`pull_request_id`)
    REFERENCES `pull_requests` (`id`),
  CONSTRAINT `pull_request_history_ibfk_2`
    FOREIGN KEY (`actor_id`)
    REFERENCES `users` (`id`))
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8;

-- -----------------------------------------------------
-- Table `repo_milestones`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `repo_milestones` ;

CREATE TABLE IF NOT EXISTS `repo_milestones` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `repo_id` INT(11) NULL DEFAULT NULL,
  `name` VARCHAR(24) NOT NULL,
  PRIMARY KEY (`id`) ,
  CONSTRAINT `repo_milestones_ibfk_1`
    FOREIGN KEY (`repo_id`)
    REFERENCES `projects` (`id`))
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8;

-- -----------------------------------------------------
-- Table `watchers`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `watchers` ;

CREATE TABLE IF NOT EXISTS `watchers` (
  `repo_id` INT(11) NOT NULL,
  `user_id` INT(11) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`repo_id`, `user_id`) ,
  CONSTRAINT `watchers_ibfk_1`
    FOREIGN KEY (`repo_id`)
    REFERENCES `projects` (`id`),
  CONSTRAINT `watchers_ibfk_2`
    FOREIGN KEY (`user_id`)
    REFERENCES `users` (`id`))
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8;

SET SQL_MODE=@OLD_SQL_MODE;
SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS;
