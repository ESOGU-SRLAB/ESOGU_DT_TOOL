#include "ProductDetection.h"

ProductDetection::ProductDetection(Robot* _robot, int timeStep)
    :robot(_robot), product(Product::NONE)
{
    D1 = robot->getDistanceSensor("distance sensor small");
    D2 = robot->getDistanceSensor("distance sensor big");

    D1->enable(timeStep);
    D2->enable(timeStep);
}

void ProductDetection::run()
{
    //Read current value of sensors
    bool d1 = false;
    bool d2 = false;
    GripperState gState = gripper->getState();

    //Convert decimal value to binary for sensor
    if (D1->getValue() < 250)
        d1 = true;
    else
        d1 = false;
    if (D2->getValue() < 250)
        d2 = true;
    else
        d2 = false;

    //Determine the product
    if (gState == GripperState::OPEN) {
        if (!d1 && !d2) {
            product = Product::NONE;
        }
        else if (d1 && !d2) {
            product = Product::SODA;
        }
        else if (d1 && d2) {
            product = Product::WATER;
        }
    }
}

