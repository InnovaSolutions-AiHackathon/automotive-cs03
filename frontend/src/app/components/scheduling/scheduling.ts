import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-scheduling',
  standalone: true,
  imports: [CommonModule, FormsModule],   
  templateUrl: './scheduling.html',
  styleUrl: './scheduling.scss',
})
export class Scheduling {

  vehicles = [
    { id: 1, name: "Honda Accord 2022" },
    { id: 2, name: "Toyota Camry 2021" },
    { id: 3, name: "Tesla Model 3 2020" }
  ];

  serviceTypes = ["Oil Change", "Engine Check", "Battery Check", "Tyre Rotation"];

  vehicleId: any = '';
  serviceType: string = '';
  date: string = '';
  time: string = '';
  notes: string = '';

  error = '';

  submitSchedule(form: any) {
    if (form.invalid) {
      this.error = "Please fill all required fields.";
      return;
    }

    this.error = "";
    console.log("Schedule Submitted:", {
      vehicleId: this.vehicleId,
      serviceType: this.serviceType,
      date: this.date,
      time: this.time,
      notes: this.notes
    });

    alert("Schedule created successfully!");
  }
}