import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-warranty',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './warranty.html',
  styleUrl: './warranty.scss',
})
export class Warranty {
warranty = {
    type: "Powertrain Warranty",
    expires: "2027-03-15",
    covered: true
  };
}
