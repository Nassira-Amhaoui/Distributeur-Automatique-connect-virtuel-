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


