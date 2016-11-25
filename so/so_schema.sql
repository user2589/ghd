SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;
SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='TRADITIONAL,ALLOW_INVALID_DATES';
SET @OLD_TIME_ZONE=@@session.time_zone;

-- DROP SCHEMA IF EXISTS `ghtorrent` ;
-- CREATE SCHEMA IF NOT EXISTS `ghtorrent` DEFAULT CHARACTER SET utf8 ;
-- USE `ghtorrent` ;

DROP TABLE IF EXISTS `so_users` ;

CREATE TABLE IF NOT EXISTS `so_users` (
  `id` INT(11) NOT NULL AUTO_INCREMENT COMMENT '',
  `name` char(64),
  `email_hash` char(32),
  `reputation` INT(11) DEFAULT 0,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '',
  `website_url` VARCHAR (255) DEFAULT '' COMMENT 'do not care about longer urls',
  `location` VARCHAR (255) DEFAULT '',
  `age` TINYINT(1) NULL DEFAULT NULL,
  `views` INT(11) DEFAULT 0,
  `upvotes` INT(11) DEFAULT 0,
  `downvotes` INT(11) DEFAULT 0,
  `about_me` TEXT,
  PRIMARY KEY (`id`)  COMMENT '')
ENGINE = MyISAM
DEFAULT CHARACTER SET = utf8;


DROP TABLE IF EXISTS `so_posts` ;

CREATE TABLE IF NOT EXISTS `so_posts` (
  `id` INT(11) NOT NULL AUTO_INCREMENT COMMENT '',
  `question` TINYINT(1) DEFAULT 1,
  `title` VARCHAR(255) COMMENT 'in fact it is up to 150 chars',
  `body` TEXT COMMENT 'up to 30k chars',
  `owner_id` INT(11) NOT NULL,
  `accepted_answer` INT(11) NULL DEFAULT NULL COMMENT 'only for answers',
  `created_at` TIMESTAMP NOT NULL DEFAULT '1970-01-01 00:00:01',
  `score` SMALLINT UNSIGNED DEFAULT 0,
  `parent_id` INT(11) NULL DEFAULT NULL COMMENT 'parent question for answers',
  `views` INT(11) NOT NULL DEFAULT 0,
  `last_editor_id` INT(11) NULL DEFAULT NULL,
  `last_edited_at` TIMESTAMP NOT NULL DEFAULT '1970-01-01 00:00:01',
  `last_activity_at` TIMESTAMP NOT NULL DEFAULT '1970-01-01 00:00:01',
  `community_owned_at` TIMESTAMP NOT NULL DEFAULT '1970-01-01 00:00:01',
  `answers_count` INT(11) NOT NULL DEFAULT 0,
  `comments_count` INT(11) NOT NULL DEFAULT 0,
  `favorites_count` INT(11) NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`)  COMMENT '',
  CONSTRAINT `posts_ibfk_1`
    FOREIGN KEY (`owner_id`)
    REFERENCES `so_users` (`id`),
  CONSTRAINT `posts_ibfk_2`
    FOREIGN KEY (`last_editor_id`)
    REFERENCES `so_users` (`id`))
ENGINE = MyISAM
DEFAULT CHARACTER SET = utf8;


DROP TABLE IF EXISTS `so_tag_names` ;

CREATE TABLE IF NOT EXISTS `so_tag_names` (
  `id` INT(11) NOT NULL AUTO_INCREMENT COMMENT '',
  `name` CHAR(25) NOT NULL,
  `count` INT(11) NOT NULL DEFAULT 0,
  `excerpt_post_id` INT(11) NULL DEFAULT NULL,
  `wiki_post_id` INT(11) NULL DEFAULT NULL,
  PRIMARY KEY (`id`)  COMMENT '')
ENGINE = MyISAM
DEFAULT CHARACTER SET = utf8;


DROP TABLE IF EXISTS `so_tags` ;

CREATE TABLE IF NOT EXISTS `so_tags` (
  `tag_id` INT(11) NOT NULL,
  `post_id` INT(11) NOT NULL,
  CONSTRAINT `tags_jfbk_1`
    FOREIGN KEY (`tag_id`)
    REFERENCES `so_tag_names` (`id`),
  CONSTRAINT `tags_jfbk_2`
    FOREIGN KEY (`post_id`)
    REFERENCES `so_posts` (`id`))
ENGINE = MyISAM
DEFAULT CHARACTER SET = utf8;

-- Votes are intentionally ignored at this point
# DROP TABLE IF EXISTS `so_tags` ;
#
# CREATE TABLE IF NOT EXISTS `so_votes` (
#   `id` INT(11) NOT NULL AUTO_INCREMENT COMMENT '',
#   `post_id` INT(11) NOT NULL,
#   `vote_type_id` INT(11) NOT NULL,
#   `created_at` TIMESTAMP NOT NULL DEFAULT '1970-01-01 00:00:01',
#   CONSTRAINT `votes_jfbk_1`
#     FOREIGN KEY (`post_id`)
#     REFERENCES `so_posts` (`id`))
# ENGINE = MyISAM
# DEFAULT CHARACTER SET = utf8;

SET SQL_MODE=@OLD_SQL_MODE;
SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS;
