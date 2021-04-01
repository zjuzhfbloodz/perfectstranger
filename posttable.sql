USE `perfectlogin`;

CREATE TABLE IF NOT EXISTS `post` (
	`id` int(11) NOT NULL,
  	`username` varchar(50) NOT NULL,
  	`content` varchar(700) NOT NULL,
  	`created_date` DATE,
    `score` DOUBLE
)ENGINE=InnoDB DEFAULT CHARSET=utf8;

INSERT INTO `post` (`id`, `username`, `content`, `created_date`) VALUES (1, 'test', 'what a bad day!',NOW());
