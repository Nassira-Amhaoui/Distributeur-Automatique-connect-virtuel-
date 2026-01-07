use gestion_stock;
-- Table: User
CREATE TABLE User (
  Id_User INT AUTO_INCREMENT,
  UserName VARCHAR(50) NOT NULL,
  Email VARCHAR(100) NOT NULL,
  Date_Creation DATETIME DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT User_PK PRIMARY KEY (Id_User),
  CONSTRAINT Email_UNQ UNIQUE (Email)
) ENGINE=InnoDB;

-- Table: Produit
CREATE TABLE Produit (
  Id_Produit INT AUTO_INCREMENT,
  Nom VARCHAR(100) NOT NULL,
  N_Etage INT NOT NULL,
  Quantite INT NOT NULL,
  CONSTRAINT Produit_PK PRIMARY KEY (Id_Produit)
) ENGINE=InnoDB;

-- Table: Historique
CREATE TABLE Historique (
  Id_Historique INT AUTO_INCREMENT,
  Action VARCHAR(50) NOT NULL,
  Quantite INT NOT NULL,
  Date_Action DATETIME DEFAULT CURRENT_TIMESTAMP,
  Id_Produit INT NOT NULL,
  CONSTRAINT Historique_PK PRIMARY KEY (Id_Historique),
  CONSTRAINT Historique_Id_Produit_FK FOREIGN KEY (Id_Produit)
    REFERENCES Produit (Id_Produit)
    ON DELETE CASCADE
    ON UPDATE CASCADE
) ENGINE=InnoDB;

select * from Produit;
select * from Historique;
select * from user;

insert into utilisateurs(Id_User, UserName, email, password, Date_Creation)
values("1", "user1", "test@gmail.com", "12345", '2025-11-25'),
("2", "user2", "admin@gmail.com", "145555", '2025-11-25');
alter table utilisateurs modify password varchar(255);
alter table utilisateurs add role varchar(20) not null default 'user';
describe utilisateurs;
update utilisateurs set role = 'admin' where email = 'test@gmail.com';
select Id_User, UserName, email, role from utilisateurs;
insert into utilisateurs(Id_User, UserName, email, password, Date_Creation, role)
values("3", "user3", "test12@gmail.com", "123", '2025-11-25', "admin"),
("4", "user4", "admin12@gmail.com", "145", '2025-11-25', "user");
alter table utilisateurs modify password varchar(255) null;
alter table utilisateurs add column language varchar(10) default 'fr';
alter table utilisateurs add column theme varchar(10) default 'light';
-- Table: login_history
CREATE TABLE login_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    date_login DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES utilisateurs(Id_User)
);
SELECT * FROM login_history l JOIN utilisateurs u ON l.user_id = u.Id_User;
SELECT l.user_id, u.Id_User, u.UserName FROM login_history l LEFT JOIN utilisateurs u ON l.user_id = u.Id_User;


